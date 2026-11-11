// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov Anim Lab: a development tool to play, scrub, see and measure the body, the held gun and reference
// animations. See docs/ANIM_LAB.md.

#include "AnimLabSubsystem.h"
#include "AnimLabActor.h"
#include "AnimPoseSampling.h"
#include "ShooterBodyAnimInstance.h"
#include "ShooterWeapon.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "CanvasItem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Debug/DebugDrawService.h"
#include "Dom/JsonObject.h"
#include "DrawDebugHelpers.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"
#include "Blueprint/UserWidget.h"
#include "UObject/UObjectIterator.h"

DEFINE_LOG_CATEGORY(LogAnimLab);

namespace
{
	constexpr int32 SweepSettleFrames = 3;

	// colors that stand out on the white mannequin, the grey gun and the grey floor, and on each other
	const FColor BodyBoneColor(255, 30, 190);    // hot pink: the body skeleton
	const FColor GhostBoneColor(0, 230, 255);    // cyan: the reference animation (ghost)
	const FColor MappedPointColor(255, 230, 0);  // yellow: mapped bones
	const FColor IKGoalColor(255, 130, 0);       // orange: the IK goal of the left hand
	const FColor LabelColor(255, 255, 255);
	constexpr float BoneThickness = 0.25f;
	constexpr float JointSize = 5.0f;
	const FColor GoodColor(60, 230, 90);
	const FColor BadColor(255, 70, 60);

	const TCHAR* ClipName(EAnimLabClip Clip)
	{
		switch (Clip)
		{
		case EAnimLabClip::Hold: return TEXT("hold");
		case EAnimLabClip::Tactical: return TEXT("tactical");
		case EAnimLabClip::Empty: return TEXT("empty");
		default: return TEXT("custom");
		}
	}

	FString Vec(const FVector& V)
	{
		return FString::Printf(TEXT("(%.2f, %.2f, %.2f)"), V.X, V.Y, V.Z);
	}

	TArray<TSharedPtr<FJsonValue>> JsonArray(std::initializer_list<double> Values)
	{
		TArray<TSharedPtr<FJsonValue>> Out;
		for (const double Value : Values)
		{
			Out.Add(MakeShared<FJsonValueNumber>(FMath::RoundToDouble(Value * 10000.0) / 10000.0));
		}
		return Out;
	}

	/** "AnimLab <command>" on the console: runs in the lab of the world that typed it, or the active lab */
	void RunConsoleCommand(const TArray<FString>& Args, UWorld* World, FOutputDevice& Ar)
	{
		const FString Line = FString::Join(Args, TEXT(" "));
		UAnimLabSubsystem* Lab = World ? World->GetSubsystem<UAnimLabSubsystem>() : nullptr;
		if (!Lab || !Lab->IsActive())
		{
			if (UAnimLabSubsystem* Active = UAnimLabSubsystem::FindActive())
			{
				Lab = Active;
			}
		}
		if (!Lab && GEngine)
		{
			// "AnimLab enable" from the editor console: the play world
			for (const FWorldContext& Context : GEngine->GetWorldContexts())
			{
				if (Context.World() && (Context.WorldType == EWorldType::PIE || Context.WorldType == EWorldType::Game))
				{
					Lab = Context.World()->GetSubsystem<UAnimLabSubsystem>();
					break;
				}
			}
		}
		if (!Lab)
		{
			Ar.Log(TEXT("AnimLab: no game world. Start Play In Editor first."));
			return;
		}
		Lab->Command(Line.IsEmpty() ? TEXT("status") : Line);
	}

	FAutoConsoleCommandWithWorldArgsAndOutputDevice AnimLabCommand(
		TEXT("AnimLab"),
		TEXT("Anim Lab development tool. 'AnimLab help' lists the commands."),
		FConsoleCommandWithWorldArgsAndOutputDeviceDelegate::CreateStatic(&RunConsoleCommand));
}

bool UAnimLabSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
	return false;
#else
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
#endif
}

void UAnimLabSubsystem::Deinitialize()
{
	SetActive(false);
	Super::Deinitialize();
}

TStatId UAnimLabSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UAnimLabSubsystem, STATGROUP_Tickables);
}

UAnimLabSubsystem* UAnimLabSubsystem::FindActive()
{
	UAnimLabSubsystem* Best = nullptr;
	if (!GEngine)
	{
		return nullptr;
	}
	for (const FWorldContext& Context : GEngine->GetWorldContexts())
	{
		UWorld* World = Context.World();
		UAnimLabSubsystem* Lab = World ? World->GetSubsystem<UAnimLabSubsystem>() : nullptr;
		if (Lab && Lab->bActive && (!Best || Lab->ActivatedAt > Best->ActivatedAt))
		{
			Best = Lab;
		}
	}
	return Best;
}

void UAnimLabSubsystem::SetActive(bool bNewActive)
{
	if (bActive == bNewActive)
	{
		return;
	}
	bActive = bNewActive;
	if (bActive)
	{
		ActivatedAt = FPlatformTime::Seconds();
		DrawHandle = UDebugDrawService::Register(TEXT("Game"), FDebugDrawDelegate::CreateUObject(this, &UAnimLabSubsystem::DrawCanvas));
		if (!LabActor.IsValid() && GetWorld())
		{
			// keys and start commands come from a lab actor: make one when the level has none
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			AAnimLabActor* Actor = GetWorld()->SpawnActor<AAnimLabActor>(Params);
			if (Actor)
			{
				Actor->bGiveWeapon = false;
				Actor->StartupCommands.Reset();
				LabActor = Actor;
			}
		}
		Log(TEXT("on. 'AnimLab help' lists the commands"));
	}
	else
	{
		UDebugDrawService::Unregister(DrawHandle);
		SetCameraMode(TEXT("fp"));
		if (AShooterWeapon* Weapon = GetWeapon())
		{
			Weapon->StopReloadPreview();
		}
	}
}

APlayerController* UAnimLabSubsystem::GetPlayerController() const
{
	return GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
}

USkeletalMeshComponent* UAnimLabSubsystem::GetBody() const
{
	const APlayerController* Controller = GetPlayerController();
	const APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
	if (const ACharacter* Character = Cast<ACharacter>(Pawn))
	{
		return Character->GetMesh();
	}
	return Pawn ? Pawn->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
}

AShooterWeapon* UAnimLabSubsystem::GetWeapon() const
{
	const APlayerController* Controller = GetPlayerController();
	const APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
	if (!Pawn)
	{
		return nullptr;
	}
	// the weapon actor is not attached (only its meshes are): the owned weapon that is not hidden
	for (TActorIterator<AShooterWeapon> It(GetWorld()); It; ++It)
	{
		if (It->GetOwner() == Pawn && !It->IsHidden())
		{
			return *It;
		}
	}
	return nullptr;
}

// ---------------------------------------------------------------------------------------------------------------------
// references

namespace
{
	USceneComponent* FindActorComponent(UWorld* World, const FString& Name)
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			bool bMatch = It->GetName() == Name;
#if WITH_EDITOR
			bMatch = bMatch || It->GetActorLabel() == Name;
#endif
			if (bMatch)
			{
				if (USkeletalMeshComponent* Mesh = It->FindComponentByClass<USkeletalMeshComponent>())
				{
					return Mesh;
				}
				return It->GetRootComponent();
			}
		}
		return nullptr;
	}
}

bool UAnimLabSubsystem::Resolve(const FString& Ref, FTransform& OutWorld, FString* OutError) const
{
	FString SpaceName = Ref;
	FString BoneText;
	Ref.Split(TEXT(":"), &SpaceName, &BoneText);
	const FName Bone = BoneText.IsEmpty() ? NAME_None : FName(*BoneText);
	auto Fail = [&](const FString& Reason)
	{
		if (OutError)
		{
			*OutError = FString::Printf(TEXT("%s: %s"), *Ref, *Reason);
		}
		return false;
	};

	// a bone or socket of a component
	USceneComponent* Component = nullptr;
	if (SpaceName == TEXT("body"))
	{
		Component = GetBody();
	}
	else if (SpaceName == TEXT("gun"))
	{
		AShooterWeapon* Weapon = GetWeapon();
		Component = Weapon ? Weapon->GetThirdPersonMesh() : nullptr;
	}
	else if (SpaceName.StartsWith(TEXT("@")))
	{
		Component = FindActorComponent(GetWorld(), SpaceName.Mid(1));
	}
	else if (SpaceName == TEXT("ghost"))
	{
		const int32 Index = FindGhostBone(Bone);
		if (Index == INDEX_NONE)
		{
			return Fail(TEXT("no such ghost bone (or no ghost)"));
		}
		OutWorld = GhostWorld[Index];
		return true;
	}
	else if (SpaceName == TEXT("mapped"))
	{
		for (const FAnimLabMap& Map : Maps)
		{
			if (Map.BodyBone == Bone)
			{
				const int32 Index = FindGhostBone(Map.GhostBone);
				if (Index == INDEX_NONE)
				{
					return Fail(TEXT("the ghost bone of the map is missing"));
				}
				OutWorld = Map.Offset * GhostWorld[Index];
				return true;
			}
		}
		return Fail(TEXT("no map for this body bone ('AnimLab map <bodybone> <ghostbone>')"));
	}
	else if (SpaceName == TEXT("tip") || SpaceName == TEXT("ghosttip"))
	{
		// the end of a finger with no end bone, as the body aim computes it: the last joint, plus the last segment
		// (the segment before it, turned as the last bone turns) times FingerTipLength
		FTransform Before, Last;
		if (SpaceName == TEXT("tip"))
		{
			const USkeletalMeshComponent* Body = GetBody();
			const FName Parent = Body && Body->GetBoneIndex(Bone) != INDEX_NONE ? Body->GetParentBone(Bone) : NAME_None;
			if (Parent.IsNone())
			{
				return Fail(TEXT("no such body bone, or it has no parent"));
			}
			Before = Body->GetSocketTransform(Parent, RTS_World);
			Last = Body->GetSocketTransform(Bone, RTS_World);
		}
		else
		{
			const int32 Index = FindGhostBone(Bone);
			if (Index == INDEX_NONE || !GhostWorld.IsValidIndex(GhostParents[Index]))
			{
				return Fail(TEXT("no such ghost bone, or it has no parent"));
			}
			Before = GhostWorld[GhostParents[Index]];
			Last = GhostWorld[Index];
		}
		const USkeletalMeshComponent* Body = GetBody();
		const UShooterBodyAnimInstance* Anim = Body ? Cast<UShooterBodyAnimInstance>(Body->GetAnimInstance()) : nullptr;
		const float Length = Anim ? Anim->AimSettings.FingerTipLength : 0.85f;
		const FVector Segment = Last.GetRotation().RotateVector(Before.GetRotation().UnrotateVector(Last.GetLocation() - Before.GetLocation()));
		OutWorld = FTransform(Last.GetRotation(), Last.GetLocation() + Segment * Length);
		return true;
	}
	else if (SpaceName == TEXT("ik"))
	{
		const USkeletalMeshComponent* Body = GetBody();
		const UShooterBodyAnimInstance* Anim = Body ? Cast<UShooterBodyAnimInstance>(Body->GetAnimInstance()) : nullptr;
		if (!Anim || !Anim->GetLastOtherHandTarget(OutWorld))
		{
			return Fail(TEXT("no hand IK in the last pose"));
		}
		return true;
	}
	else if (SpaceName == TEXT("cam"))
	{
		const APlayerController* Controller = GetPlayerController();
		if (!Controller || !Controller->PlayerCameraManager)
		{
			return Fail(TEXT("no camera"));
		}
		OutWorld = FTransform(Controller->PlayerCameraManager->GetCameraRotation(), Controller->PlayerCameraManager->GetCameraLocation());
		return true;
	}
	else if (SpaceName == TEXT("world"))
	{
		OutWorld = FTransform::Identity;
		return true;
	}
	else
	{
		return Fail(TEXT("unknown space (body, gun, ghost, mapped, tip, ghosttip, ik, cam, world, @actor)"));
	}

	if (!Component)
	{
		return Fail(TEXT("not present now"));
	}
	if (Bone.IsNone())
	{
		OutWorld = Component->GetComponentTransform();
		return true;
	}
	if (!Component->DoesSocketExist(Bone))
	{
		return Fail(TEXT("no such bone or socket"));
	}
	OutWorld = Component->GetSocketTransform(Bone, RTS_World);
	return true;
}

// ---------------------------------------------------------------------------------------------------------------------
// clock

const UAnimSequence* UAnimLabSubsystem::GetGhostAnimation() const
{
	if (Clip == EAnimLabClip::Custom)
	{
		return CustomAnimation;
	}
	const AShooterWeapon* Weapon = GetWeapon();
	if (!Weapon || !Weapon->HasHandsAnimation())
	{
		return nullptr;
	}
	const FWeaponHands& Hands = Weapon->GetHands();
	switch (Clip)
	{
	case EAnimLabClip::Tactical: return Hands.TacticalReloadAnimation;
	case EAnimLabClip::Empty: return Hands.EmptyReloadAnimation ? Hands.EmptyReloadAnimation.Get() : Hands.TacticalReloadAnimation.Get();
	default: return Hands.HoldAnimation;
	}
}

float UAnimLabSubsystem::GetClipLength() const
{
	const AShooterWeapon* Weapon = GetWeapon();
	if ((Clip == EAnimLabClip::Tactical || Clip == EAnimLabClip::Empty) && Weapon)
	{
		return Weapon->GetReloadClipLength(Clip == EAnimLabClip::Empty);
	}
	const UAnimSequence* Animation = GetGhostAnimation();
	return Animation ? Animation->GetPlayLength() : 0.0f;
}

float UAnimLabSubsystem::GetFrameRate() const
{
	const UAnimSequence* Animation = GetGhostAnimation();
	const double Fps = Animation ? Animation->GetSamplingFrameRate().AsDecimal() : 0.0;
	return Fps > 1.0 ? static_cast<float>(Fps) : 30.0f;
}

void UAnimLabSubsystem::SetTime(float NewTime)
{
	Time = FMath::Clamp(NewTime, 0.0f, FMath::Max(GetClipLength(), 0.0f));
}

void UAnimLabSubsystem::ApplyClock()
{
	AShooterWeapon* Weapon = GetWeapon();
	if (!Weapon)
	{
		return;
	}
	if (Clip == EAnimLabClip::Tactical || Clip == EAnimLabClip::Empty)
	{
		Weapon->PreviewReload(Clip == EAnimLabClip::Empty, Time);
	}
	else if (Weapon->IsReloadPreview())
	{
		Weapon->StopReloadPreview();
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// ghost

int32 UAnimLabSubsystem::FindGhostBone(FName Bone) const
{
	const int32 Index = GhostNames.IndexOfByKey(Bone);
	return GhostWorld.IsValidIndex(Index) ? Index : INDEX_NONE;
}

void UAnimLabSubsystem::UpdateGhost()
{
	GhostWorld.Reset();
	const UAnimSequence* Animation = bGhost ? GetGhostAnimation() : nullptr;
	const USkeleton* Skeleton = Animation ? Animation->GetSkeleton() : nullptr;
	TArray<FTransform> Pose;
	if (!Skeleton || !UnrealTarkov::AnimSampling::SamplePose(Animation, Time, Pose))
	{
		return;
	}
	const FReferenceSkeleton& RefSkeleton = Skeleton->GetReferenceSkeleton();
	GhostNames.SetNum(RefSkeleton.GetNum());
	GhostParents.SetNum(RefSkeleton.GetNum());
	for (int32 Index = 0; Index < RefSkeleton.GetNum(); ++Index)
	{
		GhostNames[Index] = RefSkeleton.GetBoneName(Index);
		GhostParents[Index] = RefSkeleton.GetParentIndex(Index);
	}

	// the align bone of the ghost goes on its target: Pose[Align] * Rig = Target
	FTransform Rig = FTransform::Identity;
	const int32 Align = RefSkeleton.FindBoneIndex(GhostAlignBone);
	FTransform Target;
	if (Align != INDEX_NONE && Resolve(GhostAlignTo, Target))
	{
		Rig = Pose[Align].Inverse() * Target;
	}
	else if (const USkeletalMeshComponent* Body = GetBody())
	{
		Rig = Body->GetComponentTransform();
	}
	GhostWorld.SetNum(Pose.Num());
	for (int32 Index = 0; Index < Pose.Num(); ++Index)
	{
		GhostWorld[Index] = Pose[Index] * Rig;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// presets

void UAnimLabSubsystem::PresetHands()
{
	AShooterWeapon* Weapon = GetWeapon();
	if (!Weapon || !Weapon->HasHandsAnimation())
	{
		Log(TEXT("preset hands: the held gun has no hands animation (FWeaponHands)"));
		return;
	}
	const FWeaponHands& Hands = Weapon->GetHands();
	const FName BodyLeft = Weapon->GetReload().MagazineHandBone;

	Clip = EAnimLabClip::Hold;
	bPlaying = false;
	SetTime(0.0f);
	ApplyClock();
	bGhost = true;
	GhostAlignBone = Hands.GunBone;
	GhostAlignTo = FString::Printf(TEXT("gun:%s"), *Hands.GunBone.ToString());
	UpdateGhost();

	// the left hand follows the animation hand with the weapon offset; the right hand is calibrated on the hold pose
	Maps.Reset();
	Maps.Add({ BodyLeft, Hands.HandBone, Hands.HandOffset });
	FString RightGhost = Hands.HandBone.ToString().Replace(TEXT("_L"), TEXT("_R"), ESearchCase::CaseSensitive);
	const FString RightBody = BodyLeft.ToString().Replace(TEXT("_l"), TEXT("_r"), ESearchCase::CaseSensitive);
	Command(FString::Printf(TEXT("map %s %s"), *RightBody, *RightGhost));

	Measures.Reset();
	Measures.Add({ TEXT("L hand vs mapped"), FString::Printf(TEXT("body:%s"), *BodyLeft.ToString()), FString::Printf(TEXT("mapped:%s"), *BodyLeft.ToString()) });
	Measures.Add({ TEXT("L hand vs IK goal"), FString::Printf(TEXT("body:%s"), *BodyLeft.ToString()), TEXT("ik") });
	Measures.Add({ TEXT("R hand vs mapped"), FString::Printf(TEXT("body:%s"), *RightBody), FString::Printf(TEXT("mapped:%s"), *RightBody) });
	Watches = { FString::Printf(TEXT("mapped:%s"), *BodyLeft.ToString()), FString::Printf(TEXT("body:%s"), *BodyLeft.ToString()) };
	// the hands only: the whole rig has its arm roots far from the body
	const FString RightHand = Hands.HandBone.ToString().Replace(TEXT("_L"), TEXT("_R"), ESearchCase::CaseSensitive);
	Skeletons = { FString::Printf(TEXT("ghost:%s"), *Hands.HandBone.ToString()), FString::Printf(TEXT("ghost:%s"), *RightHand),
		FString::Printf(TEXT("body:%s"), *BodyLeft.ToString()), FString::Printf(TEXT("body:%s"), *RightBody) };
	Space = TEXT("gun");
	Log(FString::Printf(TEXT("preset hands: ghost %s aligned on %s, maps %d, measures %d"), *Hands.HoldAnimation->GetName(), *GhostAlignTo, Maps.Num(), Measures.Num()));
}

void UAnimLabSubsystem::PresetFingers()
{
	AShooterWeapon* Weapon = GetWeapon();
	if (!Weapon || !Weapon->HasHandsAnimation() || Weapon->GetHands().Fingers.IsEmpty())
	{
		Log(TEXT("preset fingers: the held gun has no hands animation with fingers (FWeaponHands::Fingers)"));
		return;
	}
	// one measure per finger: the end of the body finger against the end of the animation finger (its end bone, or
	// the same estimate as the body when it has none)
	Measures.RemoveAll([](const FAnimLabMeasure& M) { return M.Name.EndsWith(TEXT(" tip")); });
	int32 Added = 0;
	for (const FWeaponHandsFinger& Finger : Weapon->GetHands().Fingers)
	{
		const int32 N = Finger.BodyBones.Num();
		if (N < 2 || Finger.AnimationBones.Num() < N)
		{
			continue;
		}
		const FString BodyLast = Finger.BodyBones.Last().ToString();
		const FString Goal = Finger.AnimationBones.Num() > N ? FString::Printf(TEXT("ghost:%s"), *Finger.AnimationBones[N].ToString())
			: FString::Printf(TEXT("ghosttip:%s"), *Finger.AnimationBones[N - 1].ToString());
		// index_03_l -> "l index tip"
		FString Name = BodyLast;
		FString Side;
		Name.Split(TEXT("_"), &Name, nullptr);
		BodyLast.Split(TEXT("_"), nullptr, &Side, ESearchCase::IgnoreCase, ESearchDir::FromEnd);
		Measures.Add({ FString::Printf(TEXT("%s %s tip"), *Side.ToUpper(), *Name), FString::Printf(TEXT("tip:%s"), *BodyLast), Goal });
		++Added;
	}
	Log(FString::Printf(TEXT("preset fingers: %d finger tip measures"), Added));
}

// ---------------------------------------------------------------------------------------------------------------------
// camera

void UAnimLabSubsystem::SetCameraMode(const FString& Mode)
{
	struct FPreset { const TCHAR* Name; float Yaw; float Pitch; };
	static const FPreset Presets[] = {
		{ TEXT("front"), 0.0f, 10.0f }, { TEXT("left"), -90.0f, 10.0f }, { TEXT("right"), 90.0f, 10.0f },
		{ TEXT("back"), 180.0f, 20.0f }, { TEXT("top"), 180.0f, 80.0f }, { TEXT("below"), -90.0f, -45.0f } };
	for (const FPreset& Preset : Presets)
	{
		if (Mode == Preset.Name)
		{
			CameraYaw = Preset.Yaw;
			CameraPitch = Preset.Pitch;
		}
	}
	CameraMode = Mode;

	APlayerController* Controller = GetPlayerController();
	if (!Controller)
	{
		return;
	}
	const bool bFirstPerson = Mode == TEXT("fp");
	if (bFirstPerson)
	{
		if (Controller->GetPawn() && Controller->GetViewTarget() != Controller->GetPawn())
		{
			Controller->SetViewTarget(Controller->GetPawn());
		}
	}
	else
	{
		if (!Camera && GetWorld())
		{
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Camera = GetWorld()->SpawnActor<ACameraActor>(Params);
			if (Camera)
			{
				Camera->GetCameraComponent()->bConstrainAspectRatio = false;
				// no motion blur: the camera follows the hands and a blurred frame is hard to read
				FPostProcessSettings& PostProcess = Camera->GetCameraComponent()->PostProcessSettings;
				PostProcess.bOverride_MotionBlurAmount = true;
				PostProcess.MotionBlurAmount = 0.0f;
			}
		}
		UpdateCamera();
		if (Camera && Controller->GetViewTarget() != Camera)
		{
			Controller->SetViewTarget(Camera);
		}
	}
	// an outside view keeps the aim still (the mouse would move the gun)
	if (!bFirstPerson && !bLookLocked)
	{
		Controller->SetIgnoreLookInput(true);
		bLookLocked = true;
	}
	else if (bFirstPerson && bLookLocked)
	{
		Controller->SetIgnoreLookInput(false);
		bLookLocked = false;
	}
}

void UAnimLabSubsystem::UpdateCamera()
{
	APlayerController* Controller = GetPlayerController();
	if (!Camera || CameraMode == TEXT("fp") || !Controller)
	{
		return;
	}
	// the pivot: the middle of the hands, or the gun, or the pawn
	FVector Pivot;
	FTransform A, B;
	if (!CameraPivot.IsEmpty() && Resolve(CameraPivot, A))
	{
		Pivot = A.GetLocation();
	}
	else if (Resolve(TEXT("body:hand_l"), A) && Resolve(TEXT("body:hand_r"), B))
	{
		Pivot = (A.GetLocation() + B.GetLocation()) * 0.5f;
	}
	else if (Resolve(TEXT("gun"), A) || Resolve(TEXT("body"), A))
	{
		Pivot = A.GetLocation();
	}
	else
	{
		return;
	}
	const float BaseYaw = Controller->GetControlRotation().Yaw;
	const FVector Direction = FRotator(CameraPitch, BaseYaw + CameraYaw, 0.0f).Vector();
	const FVector Location = Pivot + Direction * CameraDistance;
	Camera->SetActorLocationAndRotation(Location, (-Direction).Rotation());
	Camera->GetCameraComponent()->SetFieldOfView(CameraFOV);
}

// ---------------------------------------------------------------------------------------------------------------------
// tick

void UAnimLabSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!bActive)
	{
		return;
	}

	if (bPlaying && !Sweep.bRunning)
	{
		const float Length = GetClipLength();
		float NewTime = Time + DeltaTime * Rate;
		if (Length > 0.0f && (NewTime > Length || NewTime < 0.0f))
		{
			if (bLoop)
			{
				NewTime = FMath::Fmod(NewTime + Length, Length);
			}
			else
			{
				NewTime = FMath::Clamp(NewTime, 0.0f, Length);
				bPlaying = false;
			}
		}
		Time = Length > 0.0f ? NewTime : 0.0f;
	}
	ApplyClock();
	UpdateGhost();
	UpdateCamera();
	if (bGizmos)
	{
		DrawWorld();
	}
	TickSweep();
}

// ---------------------------------------------------------------------------------------------------------------------
// drawing

void UAnimLabSubsystem::DrawSkeleton(const FString& Ref) const
{
	UWorld* World = GetWorld();
	FString SpaceName = Ref;
	FString RootText;
	Ref.Split(TEXT(":"), &SpaceName, &RootText);
	const FName Root = RootText.IsEmpty() ? NAME_None : FName(*RootText);

	if (SpaceName == TEXT("ghost"))
	{
		const int32 RootIndex = Root.IsNone() ? INDEX_NONE : FindGhostBone(Root);
		for (int32 Index = 0; Index < GhostWorld.Num(); ++Index)
		{
			const int32 Parent = GhostParents[Index];
			if (Index == RootIndex)
			{
				continue;
			}
			if (Parent == INDEX_NONE || RootIndex != INDEX_NONE)
			{
				// a subtree: the bone must have the root above it
				bool bUnder = RootIndex == INDEX_NONE;
				for (int32 Up = Index; Up != INDEX_NONE && !bUnder; Up = GhostParents[Up])
				{
					bUnder = Up == RootIndex;
				}
				if (!bUnder || Parent == INDEX_NONE)
				{
					continue;
				}
			}
			DrawDebugLine(World, GhostWorld[Parent].GetLocation(), GhostWorld[Index].GetLocation(), GhostBoneColor, false, -1.0f, SDPG_Foreground, BoneThickness);
			DrawDebugPoint(World, GhostWorld[Index].GetLocation(), JointSize, GhostBoneColor, false, -1.0f, SDPG_Foreground);
		}
		return;
	}

	USkinnedMeshComponent* Mesh = nullptr;
	if (SpaceName == TEXT("body"))
	{
		Mesh = GetBody();
	}
	else if (SpaceName == TEXT("gun") && GetWeapon())
	{
		Mesh = GetWeapon()->GetThirdPersonMesh();
	}
	else if (SpaceName.StartsWith(TEXT("@")))
	{
		Mesh = Cast<USkinnedMeshComponent>(FindActorComponent(GetWorld(), SpaceName.Mid(1)));
	}
	if (!Mesh || !Mesh->GetSkinnedAsset())
	{
		return;
	}
	const FReferenceSkeleton& RefSkeleton = Mesh->GetSkinnedAsset()->GetRefSkeleton();
	const int32 RootIndex = Root.IsNone() ? INDEX_NONE : RefSkeleton.FindBoneIndex(Root);
	for (int32 Index = 0; Index < RefSkeleton.GetNum(); ++Index)
	{
		const int32 Parent = RefSkeleton.GetParentIndex(Index);
		if (Parent == INDEX_NONE || (RootIndex != INDEX_NONE && Index != RootIndex && !RefSkeleton.BoneIsChildOf(Index, RootIndex)))
		{
			continue;
		}
		if (RootIndex != INDEX_NONE && Index == RootIndex)
		{
			continue;
		}
		DrawDebugLine(World, Mesh->GetBoneTransform(Parent).GetLocation(), Mesh->GetBoneTransform(Index).GetLocation(), BodyBoneColor, false, -1.0f, SDPG_Foreground, BoneThickness);
		DrawDebugPoint(World, Mesh->GetBoneTransform(Index).GetLocation(), JointSize, BodyBoneColor, false, -1.0f, SDPG_Foreground);
	}
}

void UAnimLabSubsystem::DrawWorld() const
{
	UWorld* World = GetWorld();
	for (const FString& Ref : Skeletons)
	{
		DrawSkeleton(Ref);
	}
	for (const FString& Ref : Watches)
	{
		FTransform T;
		if (Resolve(Ref, T))
		{
			DrawDebugCoordinateSystem(World, T.GetLocation(), T.Rotator(), AxisLength, false, -1.0f, SDPG_Foreground, 0.15f);
		}
	}
	for (const FAnimLabMeasure& Measure : Measures)
	{
		FTransform A, B;
		if (Resolve(Measure.A, A) && Resolve(Measure.B, B))
		{
			const bool bGood = FVector::Dist(A.GetLocation(), B.GetLocation()) <= Tolerance;
			DrawDebugLine(World, A.GetLocation(), B.GetLocation(), bGood ? GoodColor : BadColor, false, -1.0f, SDPG_Foreground, 0.2f);
			DrawDebugPoint(World, B.GetLocation(), 6.0f, bGood ? GoodColor : BadColor, false, -1.0f, SDPG_Foreground);
		}
	}
	// mapped bones and the IK goal: small axes in their colors
	for (const FAnimLabMap& Map : Maps)
	{
		FTransform T;
		if (Resolve(FString::Printf(TEXT("mapped:%s"), *Map.BodyBone.ToString()), T))
		{
			DrawDebugPoint(World, T.GetLocation(), 8.0f, MappedPointColor, false, -1.0f, SDPG_Foreground);
		}
	}
	FTransform IK;
	if (Resolve(TEXT("ik"), IK))
	{
		DrawDebugPoint(World, IK.GetLocation(), 8.0f, IKGoalColor, false, -1.0f, SDPG_Foreground);
	}
}

void UAnimLabSubsystem::DrawCanvas(UCanvas* Canvas, APlayerController* Controller)
{
	if (!bActive || !Canvas || (Controller && Controller->GetWorld() != GetWorld()))
	{
		return;
	}
	UFont* Font = GEngine->GetSmallFont();
	const float W = Canvas->ClipX;
	const float H = Canvas->ClipY;
	auto Text = [&](const FString& String, float X, float Y, const FColor& Color)
	{
		Canvas->SetDrawColor(FColor::Black);
		Canvas->DrawText(Font, String, X + 1.0f, Y + 1.0f);
		Canvas->SetDrawColor(Color);
		Canvas->DrawText(Font, String, X, Y);
	};
	// labels at the same place go one under the other
	TArray<FVector2D> Placed;
	auto Label = [&](const FString& Ref, const FString& String, const FColor& Color)
	{
		FTransform T;
		if (bLabels && Resolve(Ref, T))
		{
			const FVector P = Canvas->Project(T.GetLocation());
			if (P.Z > 0.0f)
			{
				FVector2D At(P.X + 6.0f, P.Y - 6.0f);
				while (Placed.ContainsByPredicate([&](const FVector2D& Other) { return FMath::Abs(Other.Y - At.Y) < 13.0f && FMath::Abs(Other.X - At.X) < 120.0f; }))
				{
					At.Y += 13.0f;
				}
				Placed.Add(At);
				Text(String, At.X, At.Y, Color);
			}
		}
	};

	// labels in the world
	if (bGizmos)
	{
		for (const FString& Ref : Watches)
		{
			Label(Ref, Ref, LabelColor);
		}
		for (const FAnimLabMeasure& Measure : Measures)
		{
			float Cm;
			if (MeasureValue(Measure, Cm))
			{
				Label(Measure.B, FString::Printf(TEXT("%s %.2f cm"), *Measure.Name, Cm), Cm <= Tolerance ? GoodColor : BadColor);
			}
		}
	}

	// panel: the measures
	float Y = 80.0f;
	Text(FString::Printf(TEXT("ANIM LAB  space %s  tolerance %.1f cm"), *Space, Tolerance), 20.0f, Y, FColor::White);
	Y += 16.0f;
	for (const FAnimLabMeasure& Measure : Measures)
	{
		float Cm;
		const bool bValid = MeasureValue(Measure, Cm);
		Text(bValid ? FString::Printf(TEXT("%-20s %6.2f cm"), *Measure.Name, Cm) : FString::Printf(TEXT("%-20s   --"), *Measure.Name),
			20.0f, Y, !bValid ? FColor(150, 150, 150) : Cm <= Tolerance ? GoodColor : BadColor);
		Y += 14.0f;
	}

	// timeline
	const float Length = GetClipLength();
	const float X0 = W * 0.05f;
	const float X1 = W * 0.95f;
	const float BarY = H - 100.0f;
	FCanvasTileItem Back(FVector2D(X0, BarY), FVector2D(X1 - X0, 10.0f), FLinearColor(0.0f, 0.0f, 0.0f, 0.6f));
	Back.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Back);
	if (Length > 0.0f)
	{
		const float Fill = (X1 - X0) * FMath::Clamp(Time / Length, 0.0f, 1.0f);
		FCanvasTileItem Done(FVector2D(X0, BarY), FVector2D(Fill, 10.0f), FLinearColor(0.15f, 0.6f, 1.0f, 0.8f));
		Done.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Done);

		// the reload steps of the held gun
		if (const AShooterWeapon* Weapon = GetWeapon(); Weapon && (Clip == EAnimLabClip::Tactical || Clip == EAnimLabClip::Empty))
		{
			const FWeaponReload& Reload = Weapon->GetReload();
			TArray<TPair<float, const TCHAR*>> Steps = { { Reload.MagazineOutTime, TEXT("out") }, { Reload.PouchTime, TEXT("pouch") }, { Reload.MagazineInTime, TEXT("in") } };
			if (Clip == EAnimLabClip::Empty)
			{
				Steps.Add({ Reload.BoltReleaseTime, TEXT("bolt") });
			}
			for (const TPair<float, const TCHAR*>& Step : Steps)
			{
				const float X = X0 + (X1 - X0) * FMath::Clamp(Step.Key / Length, 0.0f, 1.0f);
				FCanvasLineItem Mark(FVector2D(X, BarY - 4.0f), FVector2D(X, BarY + 14.0f));
				Mark.SetColor(FLinearColor::Yellow);
				Canvas->DrawItem(Mark);
				Text(Step.Value, X - 8.0f, BarY + 14.0f, FColor::Yellow);
			}
		}
		const float Head = X0 + Fill;
		FCanvasLineItem Line(FVector2D(Head, BarY - 6.0f), FVector2D(Head, BarY + 16.0f));
		Line.SetColor(FLinearColor::White);
		Line.LineThickness = 2.0f;
		Canvas->DrawItem(Line);
	}
	const float Fps = GetFrameRate();
	const UAnimSequence* Ghost = GetGhostAnimation();
	Text(FString::Printf(TEXT("%s  %s  t %.3f / %.3f s  frame %d / %d  rate %.3gx  %s%s%s"),
		ClipName(Clip), Ghost ? *Ghost->GetName() : TEXT("(no ghost)"), Time, Length, FMath::RoundToInt(Time * Fps),
		FMath::RoundToInt(Length * Fps), Rate, bPlaying ? TEXT("PLAYING") : TEXT("PAUSED"), bLoop ? TEXT("  loop") : TEXT(""),
		Sweep.bRunning ? *FString::Printf(TEXT("  SWEEP %d/%d"), Sweep.Index, Sweep.Times.Num()) : TEXT("")),
		X0, BarY - 20.0f, FColor::White);

	// the keys of the lab actor, wrapped to the screen width
	if (const AAnimLabActor* Actor = LabActor.Get())
	{
		TArray<FString> Lines = { FString() };
		for (const FAnimLabKey& Binding : Actor->Keys)
		{
			const FString Item = FString::Printf(TEXT("%s%s: %s"), Binding.bShift ? TEXT("Shift+") : TEXT(""), *Binding.Key.GetDisplayName(false).ToString(), *Binding.Command);
			float ItemWidth, ItemHeight, LineWidth;
			Canvas->StrLen(Font, Lines.Last() + TEXT("   ") + Item, LineWidth, ItemHeight);
			Canvas->StrLen(Font, Item, ItemWidth, ItemHeight);
			if (!Lines.Last().IsEmpty() && LineWidth > X1 - X0)
			{
				Lines.Add(FString());
			}
			Lines.Last() += (Lines.Last().IsEmpty() ? TEXT("") : TEXT("   ")) + Item;
		}
		float LineY = BarY + 30.0f;
		for (const FString& Line : Lines)
		{
			Text(Line, X0, LineY, FColor(180, 180, 180));
			LineY += 13.0f;
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// records

bool UAnimLabSubsystem::MeasureValue(const FAnimLabMeasure& Measure, float& OutCm) const
{
	FTransform A, B;
	if (!Resolve(Measure.A, A) || !Resolve(Measure.B, B))
	{
		return false;
	}
	OutCm = FVector::Dist(A.GetLocation(), B.GetLocation());
	return true;
}

FString UAnimLabSubsystem::Describe(const FTransform& Transform) const
{
	const FRotator R = Transform.Rotator();
	return FString::Printf(TEXT("loc %s rot (P %.1f, Y %.1f, R %.1f)"), *Vec(Transform.GetLocation()), R.Pitch, R.Yaw, R.Roll);
}

TSharedPtr<FJsonObject> UAnimLabSubsystem::MakeRecord() const
{
	TSharedPtr<FJsonObject> Record = MakeShared<FJsonObject>();
	Record->SetNumberField(TEXT("t"), Time);
	Record->SetNumberField(TEXT("frame"), FMath::RoundToInt(Time * GetFrameRate()));

	TSharedPtr<FJsonObject> MeasureObject = MakeShared<FJsonObject>();
	for (const FAnimLabMeasure& Measure : Measures)
	{
		float Cm;
		if (MeasureValue(Measure, Cm))
		{
			MeasureObject->SetNumberField(Measure.Name, FMath::RoundToDouble(Cm * 1000.0) / 1000.0);
		}
		else
		{
			MeasureObject->SetField(Measure.Name, MakeShared<FJsonValueNull>());
		}
	}
	Record->SetObjectField(TEXT("measures"), MeasureObject);

	// the references in the record space
	TArray<FString> Refs = Watches;
	for (const FAnimLabMeasure& Measure : Measures)
	{
		Refs.AddUnique(Measure.A);
		Refs.AddUnique(Measure.B);
	}
	FTransform SpaceWorld = FTransform::Identity;
	Resolve(Space, SpaceWorld);
	TSharedPtr<FJsonObject> RefObject = MakeShared<FJsonObject>();
	for (const FString& Ref : Refs)
	{
		FTransform T;
		if (!Resolve(Ref, T))
		{
			continue;
		}
		const FTransform Rel = T.GetRelativeTransform(SpaceWorld);
		const FVector L = Rel.GetLocation();
		const FRotator R = Rel.Rotator();
		const FQuat Q = Rel.GetRotation();
		TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
		Item->SetArrayField(TEXT("loc"), JsonArray({ L.X, L.Y, L.Z }));
		Item->SetArrayField(TEXT("rot"), JsonArray({ R.Pitch, R.Yaw, R.Roll }));
		Item->SetArrayField(TEXT("quat"), JsonArray({ Q.X, Q.Y, Q.Z, Q.W }));
		RefObject->SetObjectField(Ref, Item);
	}
	Record->SetObjectField(TEXT("refs"), RefObject);
	return Record;
}

FString UAnimLabSubsystem::WriteJson(const FString& Name, const TSharedPtr<FJsonObject>& Root) const
{
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("AnimLab") / (Name + TEXT(".json")));
	FString Out;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
	FFileHelper::SaveStringToFile(Out, *Path);
	return Path;
}

FString UAnimLabSubsystem::TakeShot(const FString& Name, int32 Multiplier) const
{
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("AnimLab") / TEXT("Shots") / (Name + TEXT(".png")));
	if (Multiplier > 1 && GEngine)
	{
		GEngine->Exec(GetWorld(), *FString::Printf(TEXT("HighResShot %d filename=\"%s\""), Multiplier, *Path));
	}
	else
	{
		// with the UI: the debug canvas (timeline, measures, labels) is part of it
		FScreenshotRequest::RequestScreenshot(Path, true, false, false, FIntRect(), true);
	}
	return Path;
}

void UAnimLabSubsystem::TickSweep()
{
	if (!Sweep.bRunning)
	{
		return;
	}
	if (Sweep.Wait > 0)
	{
		--Sweep.Wait;
		return;
	}
	Sweep.Samples.Add(MakeShared<FJsonValueObject>(MakeRecord()));
	++Sweep.Index;
	if (Sweep.Index < Sweep.Times.Num())
	{
		SetTime(Sweep.Times[Sweep.Index]);
		Sweep.Wait = SweepSettleFrames;
		return;
	}

	// the end: one file with all the samples, and a summary of each measure
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	const UAnimSequence* Ghost = GetGhostAnimation();
	Root->SetStringField(TEXT("clip"), ClipName(Clip));
	Root->SetStringField(TEXT("animation"), Ghost ? Ghost->GetPathName() : FString());
	Root->SetStringField(TEXT("space"), Space);
	Root->SetNumberField(TEXT("tolerance"), Tolerance);
	Root->SetArrayField(TEXT("samples"), Sweep.Samples);
	const FString Path = WriteJson(Sweep.Name, Root);

	for (const FAnimLabMeasure& Measure : Measures)
	{
		float Max = -1.0f, Sum = 0.0f, MaxAt = 0.0f;
		int32 Count = 0;
		for (const TSharedPtr<FJsonValue>& Sample : Sweep.Samples)
		{
			const TSharedPtr<FJsonObject> Object = Sample->AsObject();
			double Value;
			if (Object->GetObjectField(TEXT("measures"))->TryGetNumberField(Measure.Name, Value))
			{
				Sum += Value;
				++Count;
				if (Value > Max)
				{
					Max = Value;
					MaxAt = Object->GetNumberField(TEXT("t"));
				}
			}
		}
		Log(Count > 0 ? FString::Printf(TEXT("sweep %s: %s mean %.2f cm, max %.2f cm at %.3f s (%d samples)"), *Sweep.Name, *Measure.Name, Sum / Count, Max, MaxAt, Count)
			: FString::Printf(TEXT("sweep %s: %s never resolved"), *Sweep.Name, *Measure.Name));
	}
	Log(FString::Printf(TEXT("sweep written %s"), *Path));
	Sweep.bRunning = false;
	Sweep.Samples.Reset();
	SetTime(Sweep.RestoreTime);
}

void UAnimLabSubsystem::Log(const FString& Text) const
{
	UE_LOG(LogAnimLab, Display, TEXT("ANIMLAB: %s"), *Text);
}

// ---------------------------------------------------------------------------------------------------------------------
// commands

bool UAnimLabSubsystem::Command(const FString& Line)
{
	TArray<FString> Args;
	Line.ParseIntoArrayWS(Args);
	if (Args.IsEmpty())
	{
		return false;
	}
	const FString Verb = Args[0].ToLower();
	auto Arg = [&](int32 Index, const FString& Default = FString()) { return Args.IsValidIndex(Index) ? Args[Index] : Default; };
	auto Num = [&](int32 Index, float Default) { return Args.IsValidIndex(Index) ? FCString::Atof(*Args[Index]) : Default; };
	auto Flag = [&](int32 Index, bool Current) { return Args.IsValidIndex(Index) ? FCString::Atoi(*Args[Index]) != 0 : !Current; };

	if (Verb == TEXT("enable")) { SetActive(true); return true; }
	if (Verb == TEXT("disable")) { SetActive(false); return true; }
	if (!bActive)
	{
		Log(TEXT("off: 'AnimLab enable' first"));
		return false;
	}

	const float Fps = GetFrameRate();
	if (Verb == TEXT("help"))
	{
		Log(TEXT("clock:   play | pause | toggle | step [n] | time <s> | frame <n> | rate <x> | loop [0|1] | clip <hold|tactical|empty|/Game/Anim>"));
		Log(TEXT("refs:    <space>[:<bone>]  spaces: body gun ghost mapped tip ghosttip ik cam world @<actor>"));
		Log(TEXT("gizmos:  watch <ref> | unwatch <ref|all> | measure <name> <refA> <refB> | unmeasure <name|all> | skel <space[:root]> | unskel <ref|all>"));
		Log(TEXT("         gizmo [0|1] | labels [0|1] | axes <cm> | tol <cm> | ghost [0|1] | ghost align <bone> <ref>"));
		Log(TEXT("match:   map <bodybone> <ghostbone> [weapon] (calibrates Body = Offset * Ghost now) | unmap <bodybone|all> | preset hands | preset fingers"));
		Log(TEXT("measure: get <ref> | rel <refA> <refB> | space <ref> | snap [name] | sweep [from to step name] | shot [name] [multiplier]"));
		Log(TEXT("camera:  cam <fp|front|left|right|back|top|below|orbit> | cam orbit <yaw> <pitch> [dist] | cam dist <cm> | cam pivot <ref|auto> | fov <deg>"));
		Log(TEXT("other:   status | weapon <class path> | enable | disable"));
		return true;
	}
	if (Verb == TEXT("play")) { bPlaying = true; return true; }
	if (Verb == TEXT("pause")) { bPlaying = false; return true; }
	if (Verb == TEXT("toggle")) { bPlaying = !bPlaying; return true; }
	if (Verb == TEXT("step"))
	{
		bPlaying = false;
		SetTime((FMath::RoundToFloat(Time * Fps) + Num(1, 1.0f)) / Fps);
		return true;
	}
	if (Verb == TEXT("time")) { SetTime(Num(1, 0.0f)); return true; }
	if (Verb == TEXT("frame")) { SetTime(Num(1, 0.0f) / Fps); return true; }
	if (Verb == TEXT("end")) { SetTime(GetClipLength()); return true; }
	if (Verb == TEXT("rate"))
	{
		const FString Value = Arg(1, TEXT("1"));
		Rate = Value == TEXT("up") ? Rate * 2.0f : Value == TEXT("down") ? Rate * 0.5f : FCString::Atof(*Value);
		Rate = FMath::Clamp(Rate, -8.0f, 8.0f);
		return true;
	}
	if (Verb == TEXT("loop")) { bLoop = Flag(1, bLoop); return true; }
	if (Verb == TEXT("clip"))
	{
		const FString Name = Arg(1).ToLower();
		if (Name == TEXT("next"))
		{
			Clip = Clip == EAnimLabClip::Hold ? EAnimLabClip::Tactical : Clip == EAnimLabClip::Tactical ? EAnimLabClip::Empty : EAnimLabClip::Hold;
		}
		else if (Name == TEXT("hold")) { Clip = EAnimLabClip::Hold; }
		else if (Name == TEXT("tactical")) { Clip = EAnimLabClip::Tactical; }
		else if (Name == TEXT("empty")) { Clip = EAnimLabClip::Empty; }
		else
		{
			UAnimSequence* Animation = LoadObject<UAnimSequence>(nullptr, *Arg(1));
			if (!Animation)
			{
				Log(FString::Printf(TEXT("clip: no animation %s"), *Arg(1)));
				return false;
			}
			CustomAnimation = Animation;
			Clip = EAnimLabClip::Custom;
			// align the ghost on the held gun when the skeleton has the gun bone, else on the body
			const AShooterWeapon* Weapon = GetWeapon();
			const FName GunBone = Weapon ? Weapon->GetHands().GunBone : NAME_None;
			if (!GunBone.IsNone() && Animation->GetSkeleton()->GetReferenceSkeleton().FindBoneIndex(GunBone) != INDEX_NONE)
			{
				GhostAlignBone = GunBone;
				GhostAlignTo = FString::Printf(TEXT("gun:%s"), *GunBone.ToString());
			}
			else
			{
				GhostAlignBone = Animation->GetSkeleton()->GetReferenceSkeleton().GetBoneName(0);
				GhostAlignTo = TEXT("body");
			}
		}
		SetTime(0.0f);
		Log(FString::Printf(TEXT("clip %s, %.3f s"), ClipName(Clip), GetClipLength()));
		return true;
	}

	if (Verb == TEXT("watch")) { Watches.AddUnique(Arg(1)); return true; }
	if (Verb == TEXT("unwatch")) { Arg(1) == TEXT("all") ? Watches.Reset() : (void)Watches.Remove(Arg(1)); return true; }
	if (Verb == TEXT("measure"))
	{
		if (Args.Num() < 4)
		{
			Log(TEXT("measure <name> <refA> <refB>"));
			return false;
		}
		Measures.RemoveAll([&](const FAnimLabMeasure& M) { return M.Name == Args[1]; });
		Measures.Add({ Args[1], Args[2], Args[3] });
		return true;
	}
	if (Verb == TEXT("unmeasure"))
	{
		Arg(1) == TEXT("all") ? Measures.Reset() : (void)Measures.RemoveAll([&](const FAnimLabMeasure& M) { return M.Name == Arg(1); });
		return true;
	}
	if (Verb == TEXT("skel")) { Skeletons.AddUnique(Arg(1, TEXT("ghost"))); return true; }
	if (Verb == TEXT("unskel")) { Arg(1) == TEXT("all") ? Skeletons.Reset() : (void)Skeletons.Remove(Arg(1)); return true; }
	if (Verb == TEXT("gizmo")) { bGizmos = Flag(1, bGizmos); return true; }
	if (Verb == TEXT("labels")) { bLabels = Flag(1, bLabels); return true; }
	if (Verb == TEXT("axes")) { AxisLength = Num(1, 3.0f); return true; }
	if (Verb == TEXT("tol")) { Tolerance = Num(1, 1.0f); return true; }
	if (Verb == TEXT("ghost"))
	{
		if (Arg(1) == TEXT("align"))
		{
			GhostAlignBone = FName(*Arg(2));
			GhostAlignTo = Arg(3, TEXT("body"));
			return true;
		}
		bGhost = Flag(1, bGhost);
		return true;
	}
	if (Verb == TEXT("map"))
	{
		const FName BodyBone(*Arg(1));
		const FName GhostBone(*Arg(2));
		FAnimLabMap Map{ BodyBone, GhostBone, FTransform::Identity };
		if (Arg(3) == TEXT("weapon"))
		{
			const AShooterWeapon* Weapon = GetWeapon();
			if (!Weapon)
			{
				return false;
			}
			Map.Offset = Weapon->GetHands().HandOffset;
		}
		else
		{
			// Body = Offset * Ghost, now
			FTransform Body, Ghost;
			FString Error;
			UpdateGhost();
			if (!Resolve(FString::Printf(TEXT("body:%s"), *BodyBone.ToString()), Body, &Error) || !Resolve(FString::Printf(TEXT("ghost:%s"), *GhostBone.ToString()), Ghost, &Error))
			{
				Log(FString::Printf(TEXT("map: %s"), *Error));
				return false;
			}
			Map.Offset = Body.GetRelativeTransform(Ghost);
		}
		Maps.RemoveAll([&](const FAnimLabMap& M) { return M.BodyBone == BodyBone; });
		Maps.Add(Map);
		Log(FString::Printf(TEXT("map %s = offset * ghost %s, offset %s"), *BodyBone.ToString(), *GhostBone.ToString(), *Describe(Map.Offset)));
		return true;
	}
	if (Verb == TEXT("unmap"))
	{
		Arg(1) == TEXT("all") ? Maps.Reset() : (void)Maps.RemoveAll([&](const FAnimLabMap& M) { return M.BodyBone == FName(*Arg(1)); });
		return true;
	}
	if (Verb == TEXT("preset"))
	{
		if (Arg(1) == TEXT("fingers"))
		{
			PresetFingers();
		}
		else
		{
			PresetHands();
		}
		return true;
	}

	if (Verb == TEXT("space")) { Space = Arg(1, TEXT("gun")); return true; }
	if (Verb == TEXT("get") || Verb == TEXT("rel"))
	{
		FTransform A, B = FTransform::Identity;
		FString Error;
		const FString RefB = Verb == TEXT("rel") ? Arg(2) : Space;
		if (!Resolve(Arg(1), A, &Error) || !Resolve(RefB, B, &Error))
		{
			Log(Error);
			return false;
		}
		const FTransform Rel = A.GetRelativeTransform(B);
		const FQuat Q = Rel.GetRotation();
		Log(FString::Printf(TEXT("%s in %s: %s quat (%.4f, %.4f, %.4f, %.4f)"), *Arg(1), *RefB, *Describe(Rel), Q.X, Q.Y, Q.Z, Q.W));
		return true;
	}
	if (Verb == TEXT("snap"))
	{
		const FString Name = Arg(1, FString::Printf(TEXT("snap_%s_%s"), ClipName(Clip), *FDateTime::Now().ToString(TEXT("%H%M%S"))));
		TSharedPtr<FJsonObject> Root = MakeRecord();
		Root->SetStringField(TEXT("clip"), ClipName(Clip));
		Root->SetStringField(TEXT("space"), Space);
		Log(FString::Printf(TEXT("snap written %s, shot %s"), *WriteJson(Name, Root), *TakeShot(Name, 1)));
		return true;
	}
	if (Verb == TEXT("shot"))
	{
		const FString Name = Arg(1, FString::Printf(TEXT("shot_%s"), *FDateTime::Now().ToString(TEXT("%H%M%S"))));
		Log(FString::Printf(TEXT("shot %s"), *TakeShot(Name, FCString::Atoi(*Arg(2, TEXT("1"))))));
		return true;
	}
	if (Verb == TEXT("sweep"))
	{
		const float Length = GetClipLength();
		const float From = Num(1, 0.0f);
		const float To = Num(2, Length);
		const float Step = FMath::Max(Num(3, 1.0f / Fps), 0.001f);
		Sweep = FSweep();
		Sweep.Name = Arg(4, FString::Printf(TEXT("sweep_%s_%s"), ClipName(Clip), *FDateTime::Now().ToString(TEXT("%H%M%S"))));
		for (float T = From; T <= To + 0.0001f; T += Step)
		{
			Sweep.Times.Add(T);
		}
		if (Sweep.Times.IsEmpty())
		{
			return false;
		}
		Sweep.bRunning = true;
		Sweep.RestoreTime = Time;
		bPlaying = false;
		SetTime(Sweep.Times[0]);
		Sweep.Wait = SweepSettleFrames;
		Log(FString::Printf(TEXT("sweep %s: %d samples from %.3f to %.3f s"), *Sweep.Name, Sweep.Times.Num(), From, To));
		return true;
	}

	if (Verb == TEXT("cam"))
	{
		const FString Mode = Arg(1, TEXT("fp")).ToLower();
		if (Mode == TEXT("dist")) { CameraDistance = FMath::Max(Num(2, 70.0f), 5.0f); return true; }
		if (Mode == TEXT("pivot")) { CameraPivot = Arg(2) == TEXT("auto") ? FString() : Arg(2); return true; }
		if (Mode == TEXT("orbit"))
		{
			CameraYaw = Num(2, CameraYaw);
			CameraPitch = FMath::Clamp(Num(3, CameraPitch), -89.0f, 89.0f);
			CameraDistance = Num(4, CameraDistance);
		}
		if (Mode == TEXT("yaw")) { CameraYaw += Num(2, 15.0f); SetCameraMode(TEXT("orbit")); return true; }
		if (Mode == TEXT("pitch")) { CameraPitch = FMath::Clamp(CameraPitch + Num(2, 15.0f), -89.0f, 89.0f); SetCameraMode(TEXT("orbit")); return true; }
		if (Mode == TEXT("zoom")) { CameraDistance = FMath::Max(CameraDistance * Num(2, 0.8f), 5.0f); return true; }
		SetCameraMode(Mode);
		return true;
	}
	if (Verb == TEXT("show"))
	{
		// show or hide a mesh to see the gizmos behind it: show body|gun [0|1]
		USceneComponent* Mesh = Arg(1) == TEXT("gun") ? (GetWeapon() ? GetWeapon()->GetThirdPersonMesh() : nullptr) : GetBody();
		if (!Mesh)
		{
			return false;
		}
		Mesh->SetHiddenInGame(!Flag(2, !Mesh->bHiddenInGame));
		return true;
	}
	if (Verb == TEXT("hud"))
	{
		// the game widgets of the player (health, ammo, crosshair) hide the lab text: hud [0|1]
		TArray<UUserWidget*> Widgets;
		bool bVisible = false;
		for (TObjectIterator<UUserWidget> It; It; ++It)
		{
			if (It->GetWorld() == GetWorld() && It->IsInViewport())
			{
				Widgets.Add(*It);
				bVisible |= It->GetVisibility() != ESlateVisibility::Collapsed && It->GetVisibility() != ESlateVisibility::Hidden;
			}
		}
		const bool bShow = Flag(1, bVisible);
		for (UUserWidget* Widget : Widgets)
		{
			Widget->SetVisibility(bShow ? ESlateVisibility::SelfHitTestInvisible : ESlateVisibility::Collapsed);
		}
		return true;
	}
	if (Verb == TEXT("fov")) { CameraFOV = FMath::Clamp(Num(1, 45.0f), 5.0f, 120.0f); return true; }
	if (Verb == TEXT("weapon"))
	{
		if (AAnimLabActor* Actor = LabActor.Get())
		{
			return Actor->GiveWeapon(Arg(1));
		}
		return false;
	}
	if (Verb == TEXT("status"))
	{
		const AShooterWeapon* Weapon = GetWeapon();
		const UAnimSequence* Ghost = GetGhostAnimation();
		Log(FString::Printf(TEXT("clip %s t %.3f/%.3f rate %.2f %s, weapon %s, ghost %s (%d bones, align %s on %s), cam %s, maps %d, measures %d, watches %d"),
			ClipName(Clip), Time, GetClipLength(), Rate, bPlaying ? TEXT("playing") : TEXT("paused"), Weapon ? *Weapon->GetClass()->GetName() : TEXT("none"),
			Ghost ? *Ghost->GetName() : TEXT("none"), GhostWorld.Num(), *GhostAlignBone.ToString(), *GhostAlignTo, *CameraMode, Maps.Num(), Measures.Num(), Watches.Num()));
		for (const FAnimLabMeasure& Measure : Measures)
		{
			float Cm;
			Log(MeasureValue(Measure, Cm) ? FString::Printf(TEXT("  %s = %.3f cm (%s -> %s)"), *Measure.Name, Cm, *Measure.A, *Measure.B)
				: FString::Printf(TEXT("  %s does not resolve (%s -> %s)"), *Measure.Name, *Measure.A, *Measure.B));
		}
		return true;
	}

	Log(FString::Printf(TEXT("unknown command '%s' ('AnimLab help')"), *Verb));
	return false;
}

// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov Anim Lab: put one in a level to turn the lab on in play. See docs/ANIM_LAB.md.

#include "AnimLabActor.h"
#include "AnimLabSubsystem.h"
#include "ShooterCharacter.h"
#include "ShooterWeapon.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"

AAnimLabActor::AAnimLabActor()
{
	PrimaryActorTick.bCanEverTick = true;
	// after the pawn and its weapon: the commands see this frame's pose
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;
	SetCanBeDamaged(false);

	PreferredWeapons = {
		// PORT: the props the lab gives the pawn, first that exists wins (a git ignored asset can be missing)
		FSoftClassPath(TEXT("/Game/Variant_Shooter/Blueprints/Pickups/Weapons/BP_ShooterWeapon_Rifle.BP_ShooterWeapon_Rifle_C")) };
	StartupCommands = { TEXT("hud 0"), TEXT("preset hands"), TEXT("cam left") };

	auto Add = [this](const FKey& Key, bool bShift, const TCHAR* Command) { Keys.Add({ Key, bShift, Command }); };
	Add(EKeys::P, false, TEXT("toggle"));
	Add(EKeys::Period, false, TEXT("step 1"));
	Add(EKeys::Comma, false, TEXT("step -1"));
	Add(EKeys::Period, true, TEXT("step 10"));
	Add(EKeys::Comma, true, TEXT("step -10"));
	Add(EKeys::RightBracket, false, TEXT("rate up"));
	Add(EKeys::LeftBracket, false, TEXT("rate down"));
	Add(EKeys::Home, false, TEXT("time 0"));
	Add(EKeys::End, false, TEXT("end"));
	Add(EKeys::K, false, TEXT("clip next"));
	Add(EKeys::G, false, TEXT("gizmo"));
	Add(EKeys::L, false, TEXT("labels"));
	Add(EKeys::J, false, TEXT("snap"));
	Add(EKeys::NumPadZero, false, TEXT("cam fp"));
	Add(EKeys::NumPadOne, false, TEXT("cam front"));
	Add(EKeys::NumPadThree, false, TEXT("cam right"));
	Add(EKeys::NumPadNine, false, TEXT("cam left"));
	Add(EKeys::NumPadFive, false, TEXT("cam back"));
	Add(EKeys::NumPadSeven, false, TEXT("cam top"));
	Add(EKeys::NumPadFour, false, TEXT("cam yaw -15"));
	Add(EKeys::NumPadSix, false, TEXT("cam yaw 15"));
	Add(EKeys::NumPadEight, false, TEXT("cam pitch 15"));
	Add(EKeys::NumPadTwo, false, TEXT("cam pitch -15"));
	Add(EKeys::Add, false, TEXT("cam zoom 0.8"));
	Add(EKeys::Subtract, false, TEXT("cam zoom 1.25"));
}

void AAnimLabActor::BeginPlay()
{
	Super::BeginPlay();
	if (UAnimLabSubsystem* Lab = GetWorld()->GetSubsystem<UAnimLabSubsystem>())
	{
		// register first: an active lab with no actor makes its own
		Lab->RegisterLabActor(this);
		Lab->SetActive(true);
	}
}

TSubclassOf<AShooterWeapon> AAnimLabActor::FindWeaponClass(const FString& ClassPath) const
{
	TArray<FSoftClassPath> Candidates;
	if (ClassPath.IsEmpty())
	{
		Candidates = PreferredWeapons;
	}
	else
	{
		// "/Game/Path/BP_Weapon" means its generated class
		FString Path = ClassPath;
		if (!Path.Contains(TEXT(".")))
		{
			Path += TEXT(".") + FPackageName::GetShortName(Path) + TEXT("_C");
		}
		Candidates.Add(FSoftClassPath(Path));
	}
	for (const FSoftClassPath& Candidate : Candidates)
	{
		// a git ignored asset can be missing: check the package before the load (no load warning)
		if (Candidate.IsNull() || !FPackageName::DoesPackageExist(Candidate.GetLongPackageName()))
		{
			continue;
		}
		if (UClass* Class = Candidate.TryLoadClass<AShooterWeapon>())
		{
			return Class;
		}
	}
	return nullptr;
}

bool AAnimLabActor::GiveWeapon(const FString& ClassPath)
{
	const APlayerController* Controller = GetWorld()->GetFirstPlayerController();
	AShooterCharacter* Character = Controller ? Cast<AShooterCharacter>(Controller->GetPawn()) : nullptr;
	const TSubclassOf<AShooterWeapon> Class = FindWeaponClass(ClassPath);
	if (!Character || !Class)
	{
		UE_LOG(LogAnimLab, Warning, TEXT("ANIMLAB: weapon '%s': %s"), *ClassPath, !Character ? TEXT("no shooter pawn") : TEXT("no such weapon class"));
		return false;
	}
	Character->AddWeaponClass(Class);
	UE_LOG(LogAnimLab, Display, TEXT("ANIMLAB: weapon %s"), *Class->GetName());
	return true;
}

void AAnimLabActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UAnimLabSubsystem* Lab = GetWorld()->GetSubsystem<UAnimLabSubsystem>();
	APlayerController* Controller = GetWorld()->GetFirstPlayerController();
	if (!Lab || !Controller)
	{
		return;
	}

	// a new pawn (the start, or a respawn): give the weapon, then run the start commands once
	APawn* Pawn = Controller->GetPawn();
	if (Pawn != LastPawn.Get())
	{
		LastPawn = Pawn;
		PawnFrames = 0;
	}
	if (Pawn)
	{
		++PawnFrames;
		if (PawnFrames == 1 && bGiveWeapon)
		{
			GiveWeapon(FString());
		}
		if (PawnFrames == StartupDelayFrames && !bStarted)
		{
			bStarted = true;
			for (const FString& Command : StartupCommands)
			{
				Lab->Command(Command);
			}
		}
	}

	// the keys
	if (!Lab->IsActive())
	{
		return;
	}
	const bool bShift = Controller->IsInputKeyDown(EKeys::LeftShift) || Controller->IsInputKeyDown(EKeys::RightShift);
	for (const FAnimLabKey& Binding : Keys)
	{
		if (Binding.bShift == bShift && Controller->WasInputKeyJustPressed(Binding.Key))
		{
			Lab->Command(Binding.Command);
		}
	}
}

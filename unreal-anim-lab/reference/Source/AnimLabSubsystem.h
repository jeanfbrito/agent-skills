// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov Anim Lab: a development tool to play, scrub, see and measure the body, the held gun and reference
// animations. See docs/ANIM_LAB.md.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "AnimLabSubsystem.generated.h"

class AAnimLabActor;
class ACameraActor;
class AShooterWeapon;
class UAnimSequence;
class UCanvas;
class USceneComponent;
class USkeletalMeshComponent;
class APlayerController;

DECLARE_LOG_CATEGORY_EXTERN(LogAnimLab, Log, All);

/** What the lab clock plays */
UENUM()
enum class EAnimLabClip : uint8
{
	/** The hold pose of the held gun (no reload) */
	Hold,
	/** The reload of the held gun with a round in the chamber */
	Tactical,
	/** The reload of the held gun from an empty chamber */
	Empty,
	/** Any animation asset, on the ghost only */
	Custom
};

/** A body bone that follows a ghost bone: Body = Offset * Ghost */
USTRUCT()
struct FAnimLabMap
{
	GENERATED_BODY()

	UPROPERTY() FName BodyBone;
	UPROPERTY() FName GhostBone;
	UPROPERTY() FTransform Offset = FTransform::Identity;
};

/** A distance between two references, drawn as a line and recorded */
USTRUCT()
struct FAnimLabMeasure
{
	GENERATED_BODY()

	UPROPERTY() FString Name;
	UPROPERTY() FString A;
	UPROPERTY() FString B;
};

/**
 *  The Anim Lab of a game world. It is off until an AAnimLabActor or the console command "AnimLab enable" turns it
 *  on. Then it:
 *  - plays a clock (play, pause, step frames, scrub, play rate, loop) that drives the reload of the held gun
 *    (AShooterWeapon::PreviewReload) and a ghost: the bones of a reference animation, aligned to the held gun;
 *  - draws gizmos: bone axes, skeletons, measures (distance lines), labels, and a timeline with the reload steps;
 *  - moves a lab camera around the hands (or keeps the first person view);
 *  - records references to JSON files in Saved/AnimLab (one frame, or a sweep over the clip) and takes screenshots.
 *  A reference is "<space>[:<bone>]": body, gun, ghost, mapped, ik, cam, or @<actor label>. Every feature is a
 *  console command ("AnimLab help").
 */
UCLASS()
class UNREALTARKOV_API UAnimLabSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:

	// USubsystem / FTickableGameObject
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override { return bActive; }
	virtual TStatId GetStatId() const override;

	/** Runs one lab command (the text after "AnimLab" on the console). Output goes to the log (LogAnimLab) */
	UFUNCTION(BlueprintCallable, Category="Anim Lab")
	bool Command(const FString& Line);

	UFUNCTION(BlueprintCallable, Category="Anim Lab")
	void SetActive(bool bNewActive);

	UFUNCTION(BlueprintPure, Category="Anim Lab")
	bool IsActive() const { return bActive; }

	/** A reference in world space. False (and a reason) when it does not resolve now */
	bool Resolve(const FString& Ref, FTransform& OutWorld, FString* OutError = nullptr) const;

	/** The lab actor gives the keys and the start commands */
	void RegisterLabActor(AAnimLabActor* Actor) { LabActor = Actor; }

	/** The pawn of the first local player, its body mesh, and the held gun */
	APlayerController* GetPlayerController() const;
	USkeletalMeshComponent* GetBody() const;
	AShooterWeapon* GetWeapon() const;

	/** The lab of the world with the newest activation (for the console command) */
	static UAnimLabSubsystem* FindActive();

private:

	// clock
	float GetClipLength() const;
	float GetFrameRate() const;
	void SetTime(float NewTime);
	void ApplyClock();
	const UAnimSequence* GetGhostAnimation() const;

	// ghost
	void UpdateGhost();
	int32 FindGhostBone(FName Bone) const;

	// presets
	void PresetHands();
	void PresetFingers();

	// camera
	void UpdateCamera();
	void SetCameraMode(const FString& Mode);

	// drawing
	void DrawWorld() const;
	void DrawCanvas(UCanvas* Canvas, APlayerController* Controller);
	void DrawSkeleton(const FString& Ref) const;

	// records
	TSharedPtr<class FJsonObject> MakeRecord() const;
	FString WriteJson(const FString& Name, const TSharedPtr<class FJsonObject>& Root) const;
	FString TakeShot(const FString& Name, int32 Multiplier) const;
	void TickSweep();
	FString Describe(const FTransform& Transform) const;
	bool MeasureValue(const FAnimLabMeasure& Measure, float& OutCm) const;

	void Log(const FString& Text) const;

	bool bActive = false;
	TWeakObjectPtr<AAnimLabActor> LabActor;

	// clock
	EAnimLabClip Clip = EAnimLabClip::Hold;
	UPROPERTY() TObjectPtr<UAnimSequence> CustomAnimation;
	float Time = 0.0f;
	float Rate = 1.0f;
	bool bPlaying = false;
	bool bLoop = true;

	// ghost (the bones of the reference animation in world space)
	bool bGhost = true;
	FName GhostAlignBone;
	FString GhostAlignTo;
	TArray<FTransform> GhostWorld;
	TArray<FName> GhostNames;
	TArray<int32> GhostParents;
	UPROPERTY() TArray<FAnimLabMap> Maps;

	// gizmos
	bool bGizmos = true;
	bool bLabels = true;
	float AxisLength = 3.0f;
	float Tolerance = 1.0f;
	TArray<FString> Watches;
	UPROPERTY() TArray<FAnimLabMeasure> Measures;
	TArray<FString> Skeletons;
	FString Space = TEXT("gun");

	// camera
	UPROPERTY() TObjectPtr<ACameraActor> Camera;
	FString CameraMode = TEXT("fp");
	float CameraYaw = -90.0f;
	float CameraPitch = 10.0f;
	float CameraDistance = 90.0f;
	float CameraFOV = 45.0f;
	FString CameraPivot;
	bool bLookLocked = false;

	// sweep: one record per time, after the pose settles
	struct FSweep
	{
		bool bRunning = false;
		FString Name;
		TArray<float> Times;
		int32 Index = 0;
		int32 Wait = 0;
		float RestoreTime = 0.0f;
		TArray<TSharedPtr<class FJsonValue>> Samples;
	};
	FSweep Sweep;

	FDelegateHandle DrawHandle;
	double ActivatedAt = 0.0;
};

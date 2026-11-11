// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov Anim Lab: put one in a level to turn the lab on in play. See docs/ANIM_LAB.md.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "InputCoreTypes.h"
#include "AnimLabActor.generated.h"

class AShooterWeapon;

/** A key of the lab and the lab command it runs */
USTRUCT(BlueprintType)
struct FAnimLabKey
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category="Anim Lab")
	FKey Key;

	/** The command runs only with Shift held (true) or only without it (false) */
	UPROPERTY(EditAnywhere, Category="Anim Lab")
	bool bShift = false;

	/** The text after "AnimLab" on the console */
	UPROPERTY(EditAnywhere, Category="Anim Lab")
	FString Command;
};

/**
 *  Turns the Anim Lab of its world on when play starts. It:
 *  - gives the player pawn the first weapon of PreferredWeapons that exists (again after a respawn);
 *  - runs StartupCommands once, when the pawn holds the weapon;
 *  - reads the lab keys (Keys) every frame and runs their commands.
 *  The console command "AnimLab enable" makes one with no weapon and no start commands in any level.
 */
UCLASS()
class UNREALTARKOV_API AAnimLabActor : public AActor
{
	GENERATED_BODY()

public:

	AAnimLabActor();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;

	/** Gives the player pawn a weapon class ("/Game/Path/BP_Weapon.BP_Weapon_C" or "/Game/Path/BP_Weapon"). Empty =
	 *  the first of PreferredWeapons that exists. False when there is no pawn or no such class */
	UFUNCTION(BlueprintCallable, Category="Anim Lab")
	bool GiveWeapon(const FString& ClassPath);

	/** Give the player a weapon when the pawn appears */
	UPROPERTY(EditAnywhere, Category="Anim Lab")
	bool bGiveWeapon = true;

	/** The weapons to give, in order of preference. A class that is not in the project (a git ignored asset) is skipped */
	UPROPERTY(EditAnywhere, Category="Anim Lab")
	TArray<FSoftClassPath> PreferredWeapons;

	/** Lab commands to run once the pawn holds its weapon */
	UPROPERTY(EditAnywhere, Category="Anim Lab")
	TArray<FString> StartupCommands;

	/** Frames to wait after the pawn appears before the start commands (the weapon must be held and posed) */
	UPROPERTY(EditAnywhere, Category="Anim Lab", meta=(ClampMin=1))
	int32 StartupDelayFrames = 5;

	UPROPERTY(EditAnywhere, Category="Anim Lab")
	TArray<FAnimLabKey> Keys;

private:

	TSubclassOf<AShooterWeapon> FindWeaponClass(const FString& ClassPath) const;

	TWeakObjectPtr<APawn> LastPawn;
	int32 PawnFrames = 0;
	bool bStarted = false;
};

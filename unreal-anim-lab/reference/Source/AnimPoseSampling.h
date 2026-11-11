// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov: read bones of an animation asset without a skeletal mesh component.

#pragma once

#include "CoreMinimal.h"

class UAnimSequence;

namespace UnrealTarkov::AnimSampling
{
	/** One bone of an animation at a time, in the component space of its skeleton. A bone without a track keeps its
	 *  reference pose. False when the animation has no skeleton or the bone is missing */
	UNREALTARKOV_API bool SampleBone(const UAnimSequence* Animation, FName Bone, float Time, FTransform& OutComponentSpace);

	/** All bones of an animation at a time, in the component space of its skeleton, in reference skeleton order */
	UNREALTARKOV_API bool SamplePose(const UAnimSequence* Animation, float Time, TArray<FTransform>& OutComponentSpace);
}

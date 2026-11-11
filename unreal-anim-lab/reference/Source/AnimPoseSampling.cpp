// REFERENCE IMPLEMENTATION (unreal-anim-lab skill): taken from a UE 5.8 shooter project. Port it with
// ~/Github/agent-skills/unreal-anim-lab/references/porting.md; the lines that name Shooter types are the adapters.
// UnrealTarkov: read bones of an animation asset without a skeletal mesh component.

#include "AnimPoseSampling.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"

namespace UnrealTarkov::AnimSampling
{
	namespace
	{
		FTransform SampleLocal(const UAnimSequence* Animation, const TArray<FTransform>& RefPose, int32 Index, const FAnimExtractContext& Context)
		{
			FTransform Local = RefPose.IsValidIndex(Index) ? RefPose[Index] : FTransform::Identity;
			Animation->GetBoneTransform(Local, FSkeletonPoseBoneIndex(Index), Context, false);
			return Local;
		}

		FAnimExtractContext MakeContext(const UAnimSequence* Animation, float Time)
		{
			return FAnimExtractContext(static_cast<double>(FMath::Clamp(Time, 0.0f, Animation->GetPlayLength())), false);
		}
	}

	bool SampleBone(const UAnimSequence* Animation, FName Bone, float Time, FTransform& OutComponentSpace)
	{
		const USkeleton* Skeleton = Animation ? Animation->GetSkeleton() : nullptr;
		if (!Skeleton)
		{
			return false;
		}
		const FReferenceSkeleton& RefSkeleton = Skeleton->GetReferenceSkeleton();
		int32 Index = RefSkeleton.FindBoneIndex(Bone);
		if (Index == INDEX_NONE)
		{
			return false;
		}

		// local transforms from the bone up to the root
		const FAnimExtractContext Context = MakeContext(Animation, Time);
		const TArray<FTransform>& RefPose = Skeleton->GetRefLocalPoses();
		OutComponentSpace = FTransform::Identity;
		while (Index != INDEX_NONE)
		{
			OutComponentSpace = OutComponentSpace * SampleLocal(Animation, RefPose, Index, Context);
			Index = RefSkeleton.GetParentIndex(Index);
		}
		return true;
	}

	bool SamplePose(const UAnimSequence* Animation, float Time, TArray<FTransform>& OutComponentSpace)
	{
		const USkeleton* Skeleton = Animation ? Animation->GetSkeleton() : nullptr;
		if (!Skeleton)
		{
			return false;
		}
		const FReferenceSkeleton& RefSkeleton = Skeleton->GetReferenceSkeleton();
		const TArray<FTransform>& RefPose = Skeleton->GetRefLocalPoses();
		const FAnimExtractContext Context = MakeContext(Animation, Time);

		// a parent comes before its children in the reference skeleton
		OutComponentSpace.SetNum(RefSkeleton.GetNum());
		for (int32 Index = 0; Index < RefSkeleton.GetNum(); ++Index)
		{
			const FTransform Local = SampleLocal(Animation, RefPose, Index, Context);
			const int32 Parent = RefSkeleton.GetParentIndex(Index);
			OutComponentSpace[Index] = Parent == INDEX_NONE ? Local : Local * OutComponentSpace[Parent];
		}
		return true;
	}
}

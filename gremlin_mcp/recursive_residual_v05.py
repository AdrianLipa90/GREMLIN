from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from .recursive_residual_v04 import (
    _candidate_stats,
    _canonical_sha,
    _fit,
    _flat_corr,
    _model,
    _sha_array,
    _validate_metadata,
)
from .residual_spectroscopy_v05 import analyze_residual_stack_v05

SCHEMA="GREMLIN_RECURSIVE_RESIDUAL_DECOMPOSITION_V0_5"
VERSION="0.5.0"


def recursive_residual_decomposition_v05(
    raw_runs:Sequence[Sequence[float]],
    initial_model_runs:Sequence[Sequence[float]],
    nuisance_components:Mapping[str,Sequence[Sequence[float]]],
    nuisance_metadata:Mapping[str,Mapping[str,Any]],
    *,
    sample_spacing:float=1.0,
    min_holdout_gain:float=0.01,
    min_gain_over_individual_null:float=0.005,
    global_familywise_alpha:float=0.01,
    null_count:int=1023,
    max_candidates:int=64,
    alias_abs_correlation:float=0.97,
    max_layers:int=8,
)->tuple[dict[str,Any],np.ndarray,np.ndarray]:
    raw=np.asarray(raw_runs,float)
    initial=np.asarray(initial_model_runs,float)
    if raw.shape!=initial.shape or raw.ndim!=2 or raw.shape[0]<8 or raw.shape[1]<64:
        raise ValueError("v0.5 requires equal-shape [runs,samples] with >=8 runs and >=64 samples")
    if not np.all(np.isfinite(raw)) or not np.all(np.isfinite(initial)):
        raise ValueError("raw/initial must be finite")
    if not nuisance_components:
        raise ValueError("at least one frozen nuisance component is required")
    if not (0.0<global_familywise_alpha<1.0):
        raise ValueError("global_familywise_alpha must be in (0,1)")
    if max_layers<1:
        raise ValueError("max_layers must be positive")
    if len(nuisance_components)>max_candidates:
        raise ValueError("candidate family too large for greedy v0.5; use a preregistered bank test")

    round_alpha=float(global_familywise_alpha/max_layers)
    min_null_count=int(math.ceil(1.0/round_alpha)-1)
    if null_count<min_null_count:
        raise ValueError(
            f"null_count={null_count} cannot resolve round alpha={round_alpha:.8g}; "
            f"need at least {min_null_count} null worlds"
        )

    names=sorted(str(name) for name in nuisance_components)
    _validate_metadata(nuisance_metadata,names)
    components={}
    for name in names:
        c=np.asarray(nuisance_components[name],float)
        if c.shape!=raw.shape or not np.all(np.isfinite(c)):
            raise ValueError(f"invalid nuisance component {name}")
        components[name]=c

    alias_pairs=[]
    for i,left in enumerate(names):
        for right in names[i+1:]:
            corr=abs(_flat_corr(components[left],components[right]))
            if corr>=alias_abs_correlation:
                alias_pairs.append({
                    "left":left,
                    "right":right,
                    "abs_correlation":float(corr),
                })

    stage0_packet=analyze_residual_stack_v05(
        raw,initial,sample_spacing=sample_spacing
    )
    stage0={
        "stage_index":0,
        "accepted_component":None,
        "accepted_components":[],
        "joint_coefficients":{},
        "classification":stage0_packet["classification"],
        "analysis_sha256":stage0_packet["analysis_sha256"],
        "commitments":stage0_packet["commitments"],
        "previous_stage_sha256":None,
    }
    stage0["stage_sha256"]=_canonical_sha(stage0)

    stages=[stage0]
    accepted=[]
    selection_rounds=[]

    for round_index in range(max_layers):
        remaining=[name for name in names if name not in accepted]
        if not remaining:
            break
        accepted_arrays=[components[name] for name in accepted]

        stats={}
        for name in remaining:
            stats[name]=_candidate_stats(
                raw,
                initial,
                accepted_arrays,
                components[name],
                str(nuisance_metadata[name]["null_policy"]),
                null_count,
            )

        B=min(len(stats[name]["null_conservative_gains"]) for name in remaining)
        empirical_p_floor=1.0/(B+1.0)
        if empirical_p_floor>round_alpha:
            raise RuntimeError(
                "actual null ensemble is too small for declared global alpha budget"
            )

        family_max_null=np.asarray([
            max(
                stats[name]["null_conservative_gains"][b]
                for name in remaining
            )
            for b in range(B)
        ],dtype=float)
        family_threshold=float(np.quantile(
            family_max_null,1.0-round_alpha
        ))

        passing=[]
        scored={}
        for name in remaining:
            s=stats[name]
            observed=float(s["conservative_holdout_gain"])
            family_p=float(
                (1+np.sum(family_max_null>=observed))/(B+1)
            )

            if observed<min_holdout_gain:
                decision="NO_CONSERVATIVE_HOLDOUT_GAIN"
            elif s["gain_over_individual_null_q90"]<min_gain_over_individual_null:
                decision="FAIL_INDIVIDUAL_NULL_MARGIN"
            elif s["coefficient_sign_consistent"] is not True:
                decision="CROSSFIT_COEFFICIENT_SIGN_INSTABILITY"
            elif family_p>round_alpha:
                decision="FAIL_GLOBAL_ALPHA_BUDGET"
            else:
                decision="PASS"
                passing.append((
                    family_p,
                    -s["gain_over_individual_null_q90"],
                    -observed,
                    name,
                ))

            scored[name]={
                **s,
                "familywise_empirical_p":family_p,
                "round_alpha_budget":round_alpha,
                "global_familywise_alpha":float(global_familywise_alpha),
                "declared_max_layers":int(max_layers),
                "familywise_reference_threshold":family_threshold,
                "familywise_null_worlds":int(B),
                "empirical_p_floor":float(empirical_p_floor),
                "decision":decision,
            }

        selection_rounds.append({
            "round_index":round_index+1,
            "global_familywise_alpha":float(global_familywise_alpha),
            "round_alpha_budget":round_alpha,
            "familywise_reference_threshold":family_threshold,
            "familywise_null_worlds":int(B),
            "empirical_p_floor":float(empirical_p_floor),
            "candidate_scores":scored,
        })

        if not passing:
            break

        passing.sort()
        chosen=passing[0][3]
        accepted.append(chosen)

        accepted_arrays=[components[name] for name in accepted]
        beta=_fit(raw-initial,accepted_arrays,np.arange(raw.shape[0]))
        current_model=_model(initial,accepted_arrays,beta)
        packet=analyze_residual_stack_v05(
            raw,current_model,sample_spacing=sample_spacing
        )

        stage={
            "stage_index":len(stages),
            "accepted_component":chosen,
            "accepted_components":list(accepted),
            "joint_coefficients":{
                name:float(value)
                for name,value in zip(accepted,beta)
            },
            "selection_score":scored[chosen],
            "classification":packet["classification"],
            "analysis_sha256":packet["analysis_sha256"],
            "commitments":packet["commitments"],
            "previous_stage_sha256":stages[-1]["stage_sha256"],
        }
        stage["stage_sha256"]=_canonical_sha(stage)
        stages.append(stage)

    accepted_arrays=[components[name] for name in accepted]
    final_beta=_fit(raw-initial,accepted_arrays,np.arange(raw.shape[0]))
    final_model=_model(initial,accepted_arrays,final_beta)
    final_residual=raw-final_model
    final_packet=analyze_residual_stack_v05(
        raw,final_model,sample_spacing=sample_spacing
    )

    alias_with_accepted=[
        pair for pair in alias_pairs
        if pair["left"] in accepted or pair["right"] in accepted
    ]
    if not accepted:
        status="NO_NUISANCE_LAYER_ACCEPTED"
    elif alias_with_accepted:
        status="PASS_WITH_ATTRIBUTION_ALIAS_OPEN"
    else:
        status="PASS"

    result={
        "schema":SCHEMA,
        "version":VERSION,
        "status":status,
        "raw_sha256":_sha_array(raw),
        "initial_model_sha256":_sha_array(initial),
        "accepted_layers":accepted,
        "final_joint_coefficients":{
            name:float(value)
            for name,value in zip(accepted,final_beta)
        },
        "selection_rounds":selection_rounds,
        "stages":stages,
        "alias_pairs":alias_pairs,
        "attribution_ambiguous":bool(alias_with_accepted),
        "final_packet":final_packet,
        "policy":{
            "global_familywise_alpha":float(global_familywise_alpha),
            "declared_max_layers":int(max_layers),
            "round_alpha_budget":round_alpha,
            "alpha_budget_mode":"BONFERRONI_OVER_DECLARED_RECURSIVE_ROUNDS",
            "finite_null_resolution_enforced":True,
            "formal_adaptive_fwer_proof":False,
            "candidate_must_be_frozen_before_fit":True,
            "target_derived_nuisance_forbidden":True,
            "joint_refit_after_acceptance":True,
            "mapping_order_authoritative":False,
            "destructive_denoising":False,
            "interpretation_last":True,
            "physical_mechanism_from_decomposition_only":False,
            "time_fluctuation_claim_allowed":False,
        },
    }
    result["decomposition_sha256"]=_canonical_sha(result)
    return result,final_model,final_residual


__all__=["SCHEMA","VERSION","recursive_residual_decomposition_v05"]

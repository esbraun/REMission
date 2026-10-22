"""Complete N source/configuration PROPOSAL. This module admits no execution."""
from copy import deepcopy

from .analysis import reference
from .protocol import LAW_REF, NOF1_REF
from .protocol_request import N_ESTIMAND


HISTORY = dict(schema_version="2.0.0", version="poc-analysis-history-v1-protocol-v2",
    conceptual_id="poc-analysis-history-v1", fields="resolved designated quality/ISI/indicators; typed assignments/deliveries; public design/clock/lineage",
    availability="strict available_at < cutoff; no source envelopes, excluded reports or private state")
PRIOR = dict(id="poc-nof1-prior-v2", independence="all innovations independent except displayed hierarchy",
    mu_b="Normal(19,5):scalar", sd_b="HalfNormal(3):scalar", b_raw="Normal(0,1):patient",
    population_background="Normal(0,4):C,E", sd_background="HalfNormal(1):C,E",
    population_medication_rebound="Normal(0,3):A,B,R", sd_medication_rebound="HalfNormal(1):A,B,R",
    amplitude_raw="Normal(0,1):patient,C/E/A/B/R", a="Normal(0,1):scalar",
    rho="Uniform(-.95,.95):scalar", sigma_e="HalfNormal(2):scalar",
    sigma_isi="HalfNormal(2):scalar", sigma_quality="HalfNormal(1):scalar",
    innovation="Normal(0,1):patient,public-origin-night",
    p_C="Beta(1,1):patient", p_M="Beta(1,1):patient; common between A/B",
    q="Beta(1,1):patient", beta_implementation="one conjugate factor per probability, no repeated Bernoulli likelihood")
PRIOR_REF = reference(PRIOR["id"], PRIOR)
MODEL = dict(grid="public-origin -13..T; zero state at -14; untreated -13..0; never reset at protocol activation",
    cohort="explicit predeclared compatible owned N cohort, common absolute cutoff and protocol-relative review36/72; singleton identical hierarchy",
    target="explicit target_id == saved fit seed patient == request/attempt/result patient; membership required; never first-row default",
    gate="target at least two completed randomized blocks per arm; sparse valid peers retained",
    hierarchy="b_i=mu_b+sd_b*b_raw_i; amplitude_ik=population_k+sd_k*amplitude_raw_ik; independent deviations; E retained with zero design",
    shared="mu_b,sd_b,population amplitudes,amplitude SDs,a,rho,sigma_e,sigma_isi,sigma_quality",
    individual="b,amplitudes,AR innovations/path,p_C,p_M,q",
    C=".65*C_previous+.35*I(taken continuation)", E="zero; fixed continuation restriction",
    M=".5*M_previous+.5*I(taken medication)", R=".5*R_previous+I(previous assigned B and current assigned not B)",
    residual="e=rho*e_previous+sigma_e*innovation",
    burden="b+a*sin(2*pi*public_night/21)+e-beta_C*C-beta_E*E-beta_A*D_A-beta_B*D_B+gamma*R",
    quality="Normal(10-burden/3,sigma_quality); clip0..10; round .001; infinite boundary bins",
    isi="Normal(mean burden over record14-night recall,sigma_isi); clip0..28; round1; one total likelihood",
    exposure="typed complete resolved binary component deliveries; unknown rejects; evening before report t belongs night t",
    p_C_counts="one per resolved continuation delivery", p_M_counts="one per resolved MED_A/B delivery; no baseline/washout/support counts",
    q_counts="resolved observed/missing designated quality only; pending excluded; never multiply estimand by q",
    external="none; refit cumulative unique observations from original prior")
MODEL_REFS = {purpose: reference("poc-nof1-" + purpose + "-v2", dict(MODEL,
    medication_design="current taken indicator" if purpose == "N0" else "fixed .5 medication carryover")) for purpose in ("N0", "N1")}
DIAGNOSTIC_SCHEMA = dict(id="poc-nof1-diagnostics-v1", fit="rank Rhat, bulk/tail ESS, mean MCSE by monitored quantity; divergences, tree depth, BFMI",
    integration="attempted K; eight batch means; U/L; raw/uninflated variance; mean-SE; SD/endpoints and K/2 stability; wall time and process peak RSS",
    failure="failed/abstained/inconclusive retain reason and all attempted stages; no accepted interval")
ARTIFACT_SCHEMA = dict(id="poc-nof1-artifacts-v1", posterior="NetCDF: chain/draw/patient and patient-specific public-night coordinates",
    expected_contrast="NPZ: chain/draw/target, quality_points, conditional expected next7 A-minus-B",
    predictive="NPZ: chain/draw/target/arm/night, reported_quality_points; separate availability mask",
    ownership="JSON: all consumed record IDs, distinct likelihood ownership by patient/component; H* hash and ordered membership",
    provenance="purpose/config/model/prior/estimand/history/input/request/target/seed refs and artifact bytes SHA256 verified on ingestion")
DIAGNOSTIC_REF = reference(DIAGNOSTIC_SCHEMA["id"], DIAGNOSTIC_SCHEMA)
ARTIFACT_REF = reference(ARTIFACT_SCHEMA["id"], ARTIFACT_SCHEMA)
SETTINGS = dict(family="poc-n1-v1", executable=False, backend="pymc", sampler="native_nuts", precision="float64",
    fixed_constant_policy="explicit np.float64 prior parameters/scales, interval constants and count-derived Beta shapes; verify library density normalizers independently",
    parameterization="noncentered-original-independent-prior-v1; no guide or extra potential",
    chains=4, cores=1, tune=1000, draws=1000, extension_tune=2000, extension_draws=2000,
    target_accept=.995, max_treedepth=12, blas_cores=1, rhat_max_exclusive=1.01,
    ess_bulk_min=400, ess_tail_min=400, divergences_max=0, bfmi_min_exclusive=.3,
    monitor="shared parameters; patient baseline/amplitudes; current AR states; adherence/observation probabilities; integrated target contrast",
    integration_algorithm="eight paired future adherence/AR/measurement Monte Carlo batches; rounded/clipped nightly quality; stream posterior draws",
    horizon=7, contrast="mean quality assigned A minus B; expectation per posterior draw; predictive separate",
    batches=8, initial_k=1024, max_k=65536, integration_seconds=1800,
    bootstrap_resamples=1000, bootstrap_block=20, bootstrap_seed=731981,
    mean_se=.02, sd_floor=.05, absolute_stability=.005, relative_variance=.01, relative_stability=.02,
    seed_domains=dict(inner=8101, predictive=8102, outer="purpose-specific fit seed, never outcome/assignment seed"),
    cpu=2, memory_gib=2, artifact_schema=ARTIFACT_REF, diagnostic_schema=DIAGNOSTIC_REF,
    history=HISTORY, law=LAW_REF, protocol=NOF1_REF, prior=PRIOR_REF, estimand=N_ESTIMAND)


def configuration(purpose):
    if purpose not in MODEL_REFS:
        raise ValueError("N0 or N1 configuration proposal required")
    return deepcopy(dict(SETTINGS, id="poc-n1-v1-" + purpose, purpose=purpose, model=MODEL_REFS[purpose]))


CONFIG_REFS = {purpose: reference("poc-n1-v1-" + purpose, configuration(purpose)) for purpose in MODEL_REFS}

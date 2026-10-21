# Concrete offline CLI file IO using actual PyMC draws, never a live R bridge.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2)
input <- normalizePath(args[[1]], mustWork = TRUE)
output <- args[[2]]
dir.create(output, recursive = TRUE, showWarnings = FALSE)
options(digits = 17)
library(RBesT)
library(SBC)
library(MRTAnalysis)
library(jsonlite)
summary <- list(scope = "bounded offline API/file qualification; no SBC/recovery acceptance",
                R = R.version.string, platform = R.version$platform,
                packages = lapply(c("RBesT", "SBC", "MRTAnalysis", "posterior", "rstan"),
                                  function(p) list(package = p, version = as.character(packageVersion(p)))))

prior <- mixnorm(c(1, -2, 1), sigma = 1)
weak_sd <- 5
mixtures <- list()
for (w in c(0, 0.5, 0.9, 1)) {
  # RBesT weight means weak fraction, unlike REMission informative weight w.
  mix <- if (w == 0) mixnorm(c(1, 0, weak_sd), sigma = 1) else if (w == 1) prior else
    robustify(prior, weight = 1-w, mean = 0, n = (1/weak_sd)^2)
  path <- file.path(output, paste0("rbest-native-", w, ".json"))
  write_mix_json(mix, path, digits = 16, auto_unbox = TRUE)
  restored <- read_mix_json(path)
  stopifnot(isTRUE(all.equal(unname(as.matrix(mix)), unname(as.matrix(restored)), tolerance = 1e-14)))
  m <- as.matrix(restored)
  components <- lapply(seq_len(ncol(m)), function(i) list(weight = m[1,i], mean = m[2,i], sd = m[3,i],
                              role = if (w == 0 || (w < 1 && i == ncol(m))) "weak" else "informative"))
  payload <- list(schema_version = "1.0.0", synthetic = TRUE, kind = "normal_mixture",
                  marginal_scale = "ISI_points", informative_weight = w, weak_sd = weak_sd,
                  components = components)
  write_json(payload, file.path(output, paste0("mixture-", w, ".json")), digits = 16, auto_unbox = TRUE, pretty = TRUE)
  mixtures[[as.character(w)]] <- list(weights = unname(m[1,]), means = unname(m[2,]), sds = unname(m[3,]))
}
summary$rbest <- list(native_json_roundtrip = TRUE, informative_weights = c(0,.5,.9,1),
                     weak_sd = weak_sd, mixtures = mixtures,
                     limitation = "No gMAP convergence or mixture-approximation validation claimed")

draw_path <- file.path(input, "pymc-draws.csv")
d <- read.csv(draw_path, check.names = FALSE)
stopifnot(identical(names(d), c("chain", "draw", "quantity", "value")), nrow(d) == 800L,
          identical(sort(unique(d$chain)), 0:3), identical(sort(unique(d$draw)), 0:199),
          identical(unique(d$quantity), "mu"), all(is.finite(d$value)))
backend <- SBC_backend_function(function(generated) {
  tab <- read.csv(generated$draw_file)
  draws <- array(NA_real_, dim = c(200,4,1), dimnames = list(iteration = 1:200, chain = 1:4, variable = "mu"))
  for (i in seq_len(nrow(tab))) draws[tab$draw[i]+1, tab$chain[i]+1, 1] <- tab$value[i]
  posterior::as_draws_array(draws)
}, iid_draws = FALSE, default_thin_ranks = 10)
fit <- SBC_fit(backend, list(draw_file = draw_path), cores = 1)
matrix <- SBC_fit_to_draws_matrix(fit)
stopifnot(nrow(matrix) == 800, ncol(matrix) == 1, all(is.finite(matrix)))
write.csv(d, file.path(output, "sbc-return.csv"), row.names = FALSE)
summary$sbc <- list(custom_backend = class(backend), shape = dim(matrix), actual_backend = "PyMC native NUTS file import",
                    input_coordinates = "chain 0:3, draw 0:199, quantity mu",
                    posterior_internal_coordinates = "1-based chain/iteration; file labels retained on exchange",
                    iid_draws = FALSE, default_thin_ranks = 10, calibration = "not_run")

wcls_input <- read.csv(file.path(input, "wcls-input.csv"))
analysis <- list(schema_version = "1.0.0", unit = "quality_points", centering = .5, independent_unit = "patient",
                 r_se = "hat_matrix_small_sample", python_se = "cluster_correction_not_identical")
write_json(analysis, file.path(output, "wcls-analysis.json"), auto_unbox = TRUE, pretty = TRUE)
w <- wcls(wcls_input, id = "id", outcome = "y", treatment = "action", rand_prob = "logging_probability",
          moderator_formula = ~1, control_formula = ~x, availability = "availability",
          numerator_prob = "numerator_probability", verbose = FALSE)
summary$wcls <- list(coefficients = unname(coef(w)), names = names(coef(w)),
                     printed = capture.output(print(w)), variance = "MRTAnalysis hat-matrix small-sample correction")
write_json(summary, file.path(output, "r-probes.json"), digits = 16, auto_unbox = TRUE, pretty = TRUE)
print(summary)

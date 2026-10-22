# Identical six-column UNIT rows; coefficient parity only, no SE parity claim.
library(MRTAnalysis)
library(jsonlite)
d <- read.csv('/output/unit-fixture.csv')
fit <- wcls(d, id='patient', outcome='reward', treatment='action',
    rand_prob='probability', moderator_formula=~1,
    control_formula=~prior_quality+missing_history+delivered+scaled_time,
    availability='available', numerator_prob='q', verbose=FALSE)
expected <- fromJSON('/output/python-result.json')
error <- max(abs(unname(coef(fit))-expected$coefficients))
output <- list(kind='deterministic_UNIT_not_study', R=R.version.string,
    MRTAnalysis=as.character(packageVersion('MRTAnalysis')),
    coefficients=unname(coef(fit)), names=names(coef(fit)),
    max_abs_coefficient_difference=error,
    limitation='MRTAnalysis hat-matrix correction differs; no SE or coverage parity asserted')
write_json(output, '/output/mrtanalysis-result.json', auto_unbox=TRUE, digits=16, pretty=TRUE)
print(output)
stopifnot(is.finite(error), error<1e-10)

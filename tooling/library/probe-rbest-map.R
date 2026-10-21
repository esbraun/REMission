# Offline RBesT API qualification only: tiny synthetic fit is not calibrated.
library(RBesT)
set.seed(73145)
d <- data.frame(effect=c(-1,-2,-1.5), se=c(.5,.6,.5), study=1:3)
m <- gMAP(cbind(effect,se)~1|study, data=d, family=gaussian,
          tau.prior=1, beta.prior=2, iter=80, warmup=40, thin=1, chains=2, cores=1)
a <- automixfit(m, Nc=1:2)
stopifnot(all(is.finite(as.matrix(a))))
write_mix_json(a, "tooling/library/__pycache__/outputs/r/gmap-mixture.json", digits=16)
print(a)

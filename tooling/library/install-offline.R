options(repos = c(CRAN = "https://p3m.dev/cran/__linux__/noble/2026-10-20"), Ncpus = 2)
required <- c("RBesT", "MRTAnalysis", "jsonlite", "posterior", "R6", "ggplot2",
              "stringi", "abind", "future.apply", "dplyr", "tidyr", "tidyselect", "purrr", "memoise")
install.packages(required)
stopifnot(as.character(packageVersion("RBesT")) == "1.12.0",
          as.character(packageVersion("MRTAnalysis")) == "0.4.1")
url <- "https://github.com/hyunjimoon/SBC/archive/e40a320c335460851618f7019baf79d39bbedf29.tar.gz"
archive <- tempfile(fileext = ".tar.gz")
download.file(url, archive, mode = "wb")
install.packages(archive, repos = NULL, type = "source", INSTALL_opts = c("--no-docs", "--no-help", "--no-demo"))
stopifnot(as.character(packageVersion("SBC")) == "0.5.0.0")
dir.create("/opt/remission", recursive = TRUE, showWarnings = FALSE)
packages <- installed.packages()
write.csv(packages[, c("Package", "Version", "License", "Built")], "/opt/remission/r-packages.csv", row.names = FALSE)
writeLines(capture.output(sessionInfo()), "/opt/remission/r-session.txt")

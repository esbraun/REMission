from pathlib import Path
p=Path('docs/implementation/evidence/G1-OBS-REP/implementation/curated_roles.py')
s=p.read_text().replace("ROOT = Path(__file__).resolve().parents[5]","ROOT = Path(__file__).resolve().parents[1]").replace("PREFIX = 'remission-obs2-sol-20261021'","PREFIX = 'remission-obs2-astra-review-20261021'").replace("LABEL = 'remission.task=obs2-sol-20261021'","LABEL = 'remission.task=obs2-astra-review-20261021'").replace("'remission-foundation-runtime:candidate'","'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'")
Path('.review-artifacts/curated_review.py').write_text(s)

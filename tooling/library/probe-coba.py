"""Fixed stochastic IPS public API probe; DR compatibility is explicitly rejected."""
import inspect
import json
from pathlib import Path
import numpy as np
from coba import Environment
from coba.evaluators import SequentialCB
from coba.environments.filters import OpeRewards


class Logged(Environment):
    def read(self):
        return iter([{"context": [i], "actions": [0, 1], "action": a,
                      "reward": r, "probability": p}
                     for i, (a, r, p) in enumerate([(0, 2., .5), (1, 4., .5), (1, 6., .25)])])


class FrozenPolicy:
    def score(self, context, actions, action): return [.25, .75][action]
    def predict(self, context, actions): raise AssertionError("exact IPS must score, not sample")
    def learn(self, *args, **kwargs): raise AssertionError("fixed target must never learn")


result = list(SequentialCB(record=["reward"], learn=None, eval="ips").evaluate(Logged(), FrozenPolicy()))
expected = [1., 6., 18.]
np.testing.assert_allclose([r["reward"] for r in result], expected, atol=0, rtol=0)
dr_source = inspect.getsource(OpeRewards.filter)
evaluator_source = inspect.getsource(SequentialCB._results)
assert "vw.learn" in dr_source and "OpeRewards(eval_type" in evaluator_source
report = {"COBA": "8.1.0", "fixed_stochastic_ips": result, "hand_expected": expected,
          "learning": "disabled; learn/predict methods would raise",
          "held_out_DR": "REJECTED: stock DR trains nuisance on evaluation stream; no external Q argument",
          "custom_reward_transport": "not qualified as an estimator; decision revision required"}
Path("docs/implementation/evidence/G0-LIB/coba-probes.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))

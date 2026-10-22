"""Private PA3 preparation. Never copied into the learner or HTTP input contract."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from .restricted import _generate, generate

NAMESPACE = 'pa3-external-20261021-v1'
# Frozen opaque public identities are assigned, not hashes of replay keys.
BUNDLES = ('source-7c97862d', 'source-d48331f8', 'source-28814e65')
STUDIES = (('study-a61f24e8', 'study-d9c53ba7'), ('study-4b8367d2', 'study-9fdb47a1'),
           ('study-56c39af0', 'study-e3b2a68d'))
DATASETS = (('dataset-b3e790a4', 'dataset-73a5e16c'), ('dataset-249ca8db', 'dataset-f7ad3182'),
            ('dataset-859fe61a', 'dataset-150c7d2b'))
COEFFICIENTS = ((2, 4), (2, 0), (0, 0))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def seed(namespace, scenario_index, study_index, panel_index, patient_index, cutoff_day, purpose):
    key = [namespace, scenario_index, study_index, panel_index, patient_index, cutoff_day, purpose]
    return int.from_bytes(hashlib.sha256(canonical(key).encode()).digest()[:4], 'big')


def prepare(out):
    # Importing this public contract is preparation only; no private module is
    # imported by the public contract or deterministic bridge.
    from contracts.domain.borrowing import DESIGN, SourceBundle
    out.mkdir(parents=True, exist_ok=False)
    public, private = out/'public', out/'private'
    public.mkdir(); private.mkdir()
    keys, seen = [], set()
    def allocate(namespace, scenario, study, chunk, patient, cutoff, purpose, adapter=False):
        raw = seed(namespace, scenario, study, chunk, patient, cutoff, purpose)
        value = raw % 2147483648 if adapter else raw
        if value in seen:
            raise ValueError('seed collision; frozen recipe cannot execute')
        seen.add(value)
        keys.append(dict(key=[namespace, scenario, study, chunk, patient, cutoff, purpose], raw=raw, adapter=value))
        return value
    # Reserve disjoint local development streams before source production.
    for scenario in range(3):
        allocate('pa3-development-20261021-v1', scenario, -1, 0, 0, 84, 'outcome', True)
    for scenario in range(3):
        summaries, crosswalk = [], []
        for study in range(2):
            assignment_seed = allocate(NAMESPACE, scenario, study, -1, -1, 0, 'assignment')
            labels = ['behavioral_continue']*60+['behavioral_escalate']*60
            random.Random(assignment_seed).shuffle(labels)
            chunk_seeds = [allocate(NAMESPACE, scenario, study, chunk, -1, 42, 'outcome', True) for chunk in range(5)]
            rows = []
            for participant, option in enumerate(labels):
                chunk, index = divmod(participant, 24)
                identity = f'private-{scenario}-{study}-{participant}'
                actions = [dict(day=day, option=option, assignment_id=f'{identity}-assignment-{day}') for day in (0, 14, 28)]
                request = dict(seed=chunk_seeds[chunk], index=index, patient_id=identity, through_day=42, actions=actions)
                product = _generate(request, COEFFICIENTS[scenario])
                isi = [r['record'] for r in product['records'] if r['record']['kind'] == 'isi']
                if len(isi) != 4 or any(sum(r['items']) < 0 for r in isi):
                    raise ValueError('invalid complete endpoint schedule')
                rows.append(dict(participant=identity, option=option, endpoint=sum(isi[-1]['items']), observed=product))
                crosswalk.append(dict(participant=identity, seed=chunk_seeds[chunk], index=index))
            # Plain independent scalar sample calculations; qualification tests
            # recompute from endpoint rows using NumPy, rather than this helper.
            arms = [[r['endpoint'] for r in rows if r['option'] == option] for option in ('behavioral_continue', 'behavioral_escalate')]
            means = [sum(v)/len(v) for v in arms]
            variances = [sum((x-m)**2 for x in v)/59 for v, m in zip(arms, means)]
            se = (sum(variances)/60)**.5
            if se <= 0:
                raise ValueError('nonpositive sampling SE')
            summary = dict(schema='poc-study-summary-v1/1.0.0', study_id=STUDIES[scenario][study],
                dataset_id=DATASETS[scenario][study], synthetic=True, provenance='fictional-randomized-study',
                n_continue=60, n_escalate=60, d=means[1]-means[0], se=se,
                available_at='2025-12-31T12:00:00Z', design=DESIGN)
            summary['checksum'] = digest(summary)
            summaries.append(summary)
            (private/f'{scenario}-{study}-observed.json').write_text(canonical(rows)+'\n')
        bundle = dict(schema='poc-source-bundle-v1/1.0.0', bundle_id=BUNDLES[scenario],
                      studies=summaries, source_set_sha256=digest(summaries))
        SourceBundle.model_validate_json(canonical(bundle))
        (public/f'{BUNDLES[scenario]}.json').write_text(canonical(bundle)+'\n')
        (private/f'{scenario}-crosswalk.json').write_text(canonical(crosswalk)+'\n')
    namespaces = [(r['seed'], r['index']) for scenario in range(3)
        for r in json.loads((private/f'{scenario}-crosswalk.json').read_text())]
    if len(set(namespaces)) != 720:
        raise ValueError('participant replay overlap')
    # This default-byte fixture is pinned before private core changes execute.
    fixture = dict(seed=20261021, index=0, patient_id='POC-test-01', through_day=84, actions=[])
    manifest = dict(schema='poc-pa3-private-preparation-v1', created_at=datetime.now(timezone.utc).isoformat(),
        recipe='poc-pa3-seeds-v1', seed_keys=keys, scenario_coefficients=COEFFICIENTS,
        public_bundle_ids=BUNDLES, private_participants=720, unique_replay_namespaces=720,
        local_external_streams_disjoint=True, default_v1_fixture_sha256=digest(generate(fixture)),
        files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(out.rglob('*.json'))})
    (private/'preparation.json').write_text(canonical(manifest)+'\n')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args(); manifest=prepare(args.output)
    print(canonical(dict(status='prepared', participants=manifest['private_participants'], files=manifest['files'])))

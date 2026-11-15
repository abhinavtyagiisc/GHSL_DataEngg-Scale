"""Package validated pilot results without rerunning source processing."""
import csv
import hashlib
import json
from pathlib import Path
import zipfile
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def main():
    results = ROOT / 'data/pilot_results'
    destination = ROOT / 'data/pilot_handoff'
    archive = PROJECT / 'GHSL_Weeks6_8_Pilot_Handoff.zip'
    if destination.exists() or archive.exists():
        raise FileExistsError('Preserve existing handoff; choose a new destination before rebuilding')
    for folder in (results, ROOT / 'data/district_mapping', ROOT / 'data/pilot_candidates'):
        if not (folder / '_SUCCESS').exists():
            raise ValueError(f'Incomplete results: {folder}')
        if json.loads((folder / 'validation.json').read_text())['status'] != 'PASS':
            raise ValueError(f'Validation failed: {folder}')
    report = json.loads((results / 'validation.json').read_text())
    candidates = json.loads((ROOT / 'data/pilot_candidates/validation.json').read_text())
    destination.mkdir(parents=True)
    for name in ('district_summary', 'transition_matrix', 'concentration'):
        rows = ds.dataset(results / name, format='parquet', partitioning='hive').to_table().to_pylist()
        rows.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
        with (destination / f'{name}.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    totals = report['source_totals']
    lines = [
        '# Weeks 6–8 historical pilot results', '',
        'Generated from validated saved outputs on 2026-11-06. National execution and weeks 6–8 remain incomplete.', '',
        '## Scope and validation', '',
        'Bengaluru rectangular pilot only; 1975–2020 historical epochs. Projections 2025/2030 are excluded. '
        'All district figures are intersections with the pilot, not full district totals. '
        'The same 2021 district snapshot is used across historical years.', '',
        f"Spark validated {report['fine_historical_rows']:,} fine cell-year rows and "
        f"{report['transition_rows']:,} coarse cell-period rows; "
        f"{report['district_summary_rows']:,} district/year/class summary rows. "
        'Checks include unique keys, complete trajectories, temporal footprint consistency, district population/total-built conservation, '
        'and every-column Parquet round trips for cell transitions and district summaries.', '',
        'The corrected schema regression suite passed 10 tests in 15.86 seconds. '
        'The first sandboxed test attempt failed because local Spark sockets were unavailable; '
        'the socket-enabled rerun passed.', '',
        '## Pilot totals', '',
        '| Year | Population estimate | Total built surface (km²) |',
        '| --- | ---: | ---: |',
    ]
    for year in sorted(totals, key=int):
        row = totals[year]
        lines.append(f"| {year} | {row['population']:,.2f} | {row['built_surface_m2']/1e6:,.3f} |")
    lines += ['', 'Population values are estimated counts; built surface is area, not floor space. '
              'Transition matrix row_share uses coarse-cell counts, including partial pilot-edge cells; '
              'sampled_area_km2 separately accounts for the pilot footprint.', '',
              '## Candidate screening', '',
              f"There are {candidates['screened_events']} overlapping period/component events, not distinct-town counts.", '']
    for status, count in candidates['event_counts'].items():
        lines.append(f'- {status}: {count}')
    lines += ['', 'Sensitivity results:', '', '| Connectivity | Growth threshold | Growth events | Absorption events |',
              '| --- | ---: | ---: | ---: |']
    for case in candidates['sensitivity']:
        counts = case['event_counts']
        lines.append(f"| {case['connectivity']} | {case['minimum_growth_fraction']:.0%} | "
                     f"{counts.get('independent_growth_candidate',0)} | {counts.get('metropolitan_absorption_candidate',0)} |")
    lines += ['', 'These are exploratory morphological candidates. Adjacency does not establish economic integration '
              'or administrative absorption. Pilot-edge censoring and lineage ambiguity limit interpretation. '
              'External case-study review is pending; no spatial review GeoJSON is included.', '',
              '## Sources and reproduction', '',
              'GHSL: European Commission Joint Research Centre, GHS-POP/GHS-BUILT-S R2023A and GHS-SMOD R2023A V2_0. '
              'Source manifests and grid contracts are included.', '',
              'District source: geoBoundaries gbOpen IND ADM2, boundary ID IND-ADM2-76128533, represented year 2021; '
              'Pathways Data Pvt. Ltd., lgdirectory.gov.in. '
              'Licensed under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). '
              'The source has 735 actual features despite API metadata advertising 736. '
              'Derived district mapping and summaries retain this attribution; preserve it when sharing.', '',
              'See analysis/README.md for commands. This handoff includes analysis outputs, mapping, scripts, '
              'configuration and evidence; source rasters and the large weeks 1–5 analytical input are excluded. '
              'Reproduction requires the existing weeks 1–5 integration dataset and the project Python environment.', '']
    (ROOT / 'reports/PILOT_REPORT.md').write_text('\n'.join(lines))
    paths = []
    for folder in ('src', 'scripts', 'config', 'tests', 'reports', 'data/pilot_results',
                   'data/pilot_candidates', 'data/district_mapping', 'data/pilot_handoff'):
        paths.extend(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('.') and not p.name.startswith('handoff_build'))
    paths += [ROOT / 'README.md', ROOT / 'AGENTS.md', ROOT / 'data/boundaries/IND_ADM2.provenance.json',
              PROJECT / 'integration/config/grid_contract.json', PROJECT / 'integration/config/pilot.json',
              PROJECT / 'integration/reports/download_manifest_full.json', PROJECT / 'population/requirements-lock.txt']
    manifest = {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    (destination / 'SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n')
    paths.append(destination / 'SHA256.json')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(set(paths)):
            handle.write(path, path.relative_to(PROJECT))
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
        for name, digest in manifest.items():
            assert hashlib.sha256(handle.read(name)).hexdigest() == digest, name
    print(json.dumps({'archive': str(archive), 'files': len(set(paths)), 'bytes': archive.stat().st_size,
                      'crc_and_sha256': 'PASS'}, indent=2))


if __name__ == '__main__':
    main()

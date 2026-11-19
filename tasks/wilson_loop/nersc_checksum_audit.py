"""NERSC checksum matrix: standard header CHECKSUM vs private MD5 (todo P1b)."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .common import nersc_word_checksum, read_nersc_with_status

OUT = Path('results/wilson_loop/audit_20261119_nersc')


def cold_file(path, header_checksum=None, endian='little', md5=False, alter=False):
    links = np.zeros((4, 3, 3), dtype='<c16')
    for i in range(3):
        links[:, i, i] = 1.0
    if alter:
        links[0, 0, 0] += 0.5
    payload = links.tobytes() if endian == 'little' else links.astype('>c16').tobytes()
    floating = 'IEEE64LITTLE' if endian == 'little' else 'IEEE64BIG'
    header = (b'BEGIN_HEADER\nDATATYPE=4D_SU3_GAUGE_3x3\n'
              b'DIMENSION_1=1\nDIMENSION_2=1\nDIMENSION_3=1\nDIMENSION_4=1\n'
              + f'FLOATING_POINT={floating}\n'.encode()
              + (f'CHECKSUM={header_checksum}\n'.encode() if header_checksum else b'')
              + b'END_HEADER\n')
    path.write_bytes(header + payload + (hashlib.md5(payload).digest() if md5 else b''))
    return path


def run_case(tmp, name, **kwargs):
    path = cold_file(Path(tmp) / name, **kwargs)
    try:
        array, status = read_nersc_with_status(path)
        return {'case': name, 'ok': True, 'shape': list(array.shape), 'status': status}
    except ValueError as exc:
        return {'case': name, 'ok': False, 'reason': str(exc).replace(str(tmp), '<tmp>')}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    cases = [
        run_case(tmp, 'cold_standard_ok', header_checksum='ff400000'),
        run_case(tmp, 'cold_standard_wrong', header_checksum='ff400001'),
        run_case(tmp, 'cold_standard_wrong_md5_ok', header_checksum='ff400001', md5=True),
        run_case(tmp, 'cold_standard_ok_md5_ok', header_checksum='ff400000', md5=True),
        run_case(tmp, 'cold_md5_only', md5=True),
        run_case(tmp, 'cold_absent'),
        run_case(tmp, 'cold_payload_altered', header_checksum='ff400000', alter=True),
    ]
    big = cold_file(tmp / 'big_probe', endian='big')
    with open(big, 'rb') as f:
        payload = f.read().split(b'END_HEADER\n')[1]
    big_value = nersc_word_checksum(payload, 'IEEE64BIG')
    cases.append(run_case(tmp, 'big_standard_ok', header_checksum=f'{big_value:08x}', endian='big'))
    # a zero-payload value is only a sanity print, not a check
    result = {'schema': 'wilson-nersc-checksum-matrix-v1',
              'standard_algorithm': '32-bit word sum modulo 2**32 on host-order words',
              'cold_field_checksum': 'ff400000',
              'big_field_checksum': f'{big_value:08x}',
              'cases': cases,
              'all_expected': all(
                  (case['case'] in ('cold_standard_ok', 'cold_standard_ok_md5_ok',
                                    'big_standard_ok') and case['ok'])
                  or (case['case'] not in ('cold_standard_ok', 'cold_standard_ok_md5_ok',
                                           'big_standard_ok') and not case['ok'])
                  for case in cases)}
    (OUT / 'nersc_checksum.json').write_text(json.dumps(result, indent=2) + '\n')
    for case in cases:
        print(case['case'], case['ok'], case.get('status', case.get('reason', '')))


if __name__ == '__main__':
    main()

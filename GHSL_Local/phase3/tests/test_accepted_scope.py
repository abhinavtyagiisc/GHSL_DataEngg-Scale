import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('accepted_scope',Path(__file__).resolve().parents[1]/'scripts/accept_verified_scope.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_exact_scope_inventory():
    identity=dict(tiles=['A','R8_C27'],config=dict(epochs=[1975,1980]))
    records=[dict(tile='A',year=y) for y in [1975,1980]]
    assert m.inventory(identity,records,['R8_C27'])==['A']
    for invalid in [records[:1],records+records[:1],records+[dict(tile='R8_C27',year=1975)]]:
        with pytest.raises(ValueError,match='exact verified'):m.inventory(identity,invalid,['R8_C27'])

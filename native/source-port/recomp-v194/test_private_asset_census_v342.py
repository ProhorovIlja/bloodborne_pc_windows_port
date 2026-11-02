#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V342: invented assets only; never touches owner game uploads."""
from pathlib import Path
import json
import tempfile
from private_asset_census_v342 import census,owner_root

def main():
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp)
        bb=base/'CUSA03173'/'dvdroot_ps4'
        ds=base/'Dark Souls III'/'Game'
        (bb/'chr').mkdir(parents=True)
        (ds/'chr').mkdir(parents=True)
        (ds/'map').mkdir()
        (bb/'chr'/'sample.chrbnd.dcx').write_bytes(b'DCX\0'+b'A'*7)
        (bb/'chr'/'another.bnd').write_bytes(b'BND4'+b'B'*12)
        (ds/'chr'/'model.flver').write_bytes(b'FLVER'+b'C'*7)
        (ds/'map'/'unknown.blob').write_bytes(b'D'*32)
        assert owner_root(bb)==bb
        counts=census(bb)
        assert counts['files']==2 and counts['bytes']==27
        assert counts['groups']=={'chr':2}
        assert counts['formats']['DCX compression wrapper']==1
        assert counts['formats']['BND4 asset binder']==1
        counts2=census(ds)
        assert counts2['files']==2 and counts2['bytes']==44
        assert counts2['groups']=={'chr':1,'map':1}
        assert counts2['formats']['FLVER geometry']==1
        assert counts2['formats']['unclassified']==1
        report=json.dumps({'bloodborne':counts,'dark_souls_iii':counts2})
        for private in ('sample.chrbnd.dcx','model.flver','unknown.blob',str(bb),str(ds)):
            assert private not in report
        try:
            census(base/'absent')
        except ValueError:
            pass
        else:
            raise AssertionError('missing private tree accepted')
        empty=base/'empty';empty.mkdir()
        try:
            census(empty)
        except ValueError:
            pass
        else:
            raise AssertionError('empty private tree accepted')
        linked=bb/'chr'/'link'
        try:
            linked.symlink_to(ds/'chr'/'model.flver')
        except (OSError,NotImplementedError):
            pass
        else:
            try:census(bb)
            except ValueError:pass
            else:raise AssertionError('linked private asset accepted')
    print('SHYT_V342_PRIVATE_CROSS_TITLE_ASSET_CENSUS_BOUNDED_PASS')

if __name__=='__main__':
    main()

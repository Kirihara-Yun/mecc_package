"""Package only the standalone ideal manuscript, never raw research evidence."""
from pathlib import Path
import hashlib
import json
import zipfile

P=Path(__file__).resolve().parent


def main():
    active=json.loads((P/'validation.json').read_text(encoding='utf-8')).get('pdf_file','mecc_dac2027.pdf')
    names=['mecc_dac2027.tex',active,Path(active).with_suffix('.bbl').name,'references.bib',
       'IEEEtran.cls','README.md','REQUIREMENTS_AND_FIGURE_STUDY.md',
       'WORKBUDDY_EXPERIMENT_HANDOFF.md','EXPERIMENT_MATRIX.md','ideal_assumptions.json','validation.json',
       'CITATION_COVERAGE.md','FILL_IN_GUIDE.md','visual_validation.json','figure_terms.json',
       'MECC_BEGINNER_GUIDE_ZH.md','MECC_BEGINNER_GUIDE_ZH.html','build_beginner_guide.py',
       'build_figures.py','build_ideal_figures.py','build_paper_figures.py','build_gallery.py','verify_draft.py','verify_visual_layout.py',
       'package_source.py','requirements.txt','figure_gallery_polished.pdf','editing/VISUAL_POLISH_REVIEW.md',
       'editing/before_visual_polish.tex','editing/visual_polish_diff.html',
       'editing/LINE_EDIT_REVIEW.md','editing/before_lineedit.tex','editing/lineedit_diff.html',
       'editing/FULLTEXT_READING_AND_REVISION.md','editing/before_fulltext_revision.tex','editing/fulltext_revision_diff.html']
    files=[P/n for n in names]
    files+=sorted((P/'reviews').glob('*.md'))
    files+=sorted((P/'reviews').glob('round*/*'))
    files+=[P/'reviews'/'revision_diff.html',P/'reviews'/'final_artifact_hashes.json']
    files+=sorted((P/'template').glob('*'))
    files+=sorted((P/'ideal_figures').glob('*'))
    files+=[P/'figures'/f'{n}.{ext}' for n in ['fig01_overview','fig03_retention','fig08_delivery'] for ext in ['pdf','svg','png']]
    hashes={str(p.relative_to(P)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest={'status':'HYPOTHETICAL DESIGN DRAFT -- NOT FOR SUBMISSION',
              'files_sha256':hashes,'active_pdf':active,'includes_private_or_raw_experiment_data':False,
              'note':'build_figures.py main requires the original repository for measured replay figures; schematic regeneration and ideal manuscript build are standalone.'}
    with zipfile.ZipFile(P.parent/'MECC_DAC2027_ideal_source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p,'dac2027/'+str(p.relative_to(P)).replace('\\','/'))
        z.writestr('dac2027/PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
    print('Packaged',len(files),'files:',P.parent/'MECC_DAC2027_ideal_source.zip')


if __name__=='__main__': main()

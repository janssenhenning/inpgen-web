from __future__ import annotations

import pathlib
import subprocess
from pymatgen.core import Structure
from pymatgen.io.cif import CifParser

import tempfile
from celery import Celery
from celery.utils.log import get_task_logger
import os

logger = get_task_logger(__name__)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379')


celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task(name='tasks.create_input')
def create_input(*args, **kwargs):

    try:
        return create_inpxml(*args, **kwargs)
    except Exception as exc:
        logger.exception(exc)


INPGEN_FILENAME = "inpgen.in"

def run_inpgen(folder: pathlib.Path, *args: str) -> dict[str,str]:

    with open(folder / "stdout", "w") as f_stdout:
            with open(folder / "stderr", "w") as f_stderr:
                res = subprocess.run(["inpgen", "-f", INPGEN_FILENAME,"-no_send", "-inc", '+all', *args],
                                     cwd=folder,
                                     stdout=f_stdout,
                                     stderr=f_stderr,
                                     check=False)
    # Check if successful:
    with open(folder / "stderr", "r") as f_stderr:
        error_content= f_stderr.read()

    with open(folder / "inp.xml", "r") as f:
        inpxml_content = f.read()

    if 'Run finished successfully' not in error_content:
        raise ValueError("Inpgen execution failed")

    return {
        'inp.xml': inpxml_content,
        'status': error_content
    }

def write_inpgen_file(folder: pathlib.Path, pymatgen_structure: Structure) -> None:
    pymatgen_structure.to('fleur-inpgen', folder / INPGEN_FILENAME)

def read_cif_file(cif_file: pathlib.Path, symmetrize: bool = False) -> Structure:
    cif = CifParser(cif)
    return cif.get_structures(symmetrized=symmetrize)[0]

def create_inpxml(folder, cif_file, symmetrize: bool=False):

    struc = read_cif_file(cif_file, symmetrize=symmetrize)
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        write_inpgen_file(folder, struc)
        res = run_inpgen(folder)

    return res
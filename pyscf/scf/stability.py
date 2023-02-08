#!/usr/bin/env python
# Copyright 2014-2020 The PySCF Developers. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

'''Wave Function Stability Analysis

Ref.
JCP 66, 3045 (1977); DOI:10.1063/1.434318
JCP 104, 9047 (1996); DOI:10.1063/1.471637

See also tddft/rhf.py and scf/newton_ah.py
'''

import numpy
import scipy
from functools import reduce
from pyscf import lib
from pyscf.lib import logger
from pyscf.scf import hf, hf_symm, uhf_symm, ghf_symm
from pyscf.scf import _response_functions  # noqa
from pyscf.soscf import newton_ah
from pyscf import __config__

STAB_NROOTS = getattr(__config__, 'STAB_NROOTS', 3)

def _get_internal_stability_status(mf):
    res = mf.stability(return_status=True)
    if len(res) == 4:
        return res[0], res[2]
    elif len(res) == 2:
        return res

def stable_opt_internal(mf, max_attempt=10):
    log = logger.new_logger(mf)
    mo1, stable = _get_internal_stability_status(mf)
    cyc = 0
    while (not stable and cyc < max_attempt):
        log.note('Try to optimize orbitals until stable, attempt %d' % cyc)
        dm1 = mf.make_rdm1(mo1, mf.mo_occ)
        mf = mf.run(dm1)
        mo1, stable = _get_internal_stability_status(mf)
        cyc += 1
    if not stable:
        log.note('Stability Opt failed after %d attempts' % cyc)
    return mf

def dump_status(log, stable, method_class, stab_type):
    if not stable:
        log.note(method_class + f' wavefunction has an {stab_type} instability')
    else:
        log.note(method_class + f' wavefunction is stable in the {stab_type} '
                 'stability analysis')


def rhf_stability(mf, internal=True, external=False, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    '''
    Stability analysis for RHF/RKS method.

    Args:
        mf : RHF or RKS object

    Kwargs:
        internal : bool
            Internal stability, within the RHF space.
        external : bool
            External stability. Including the RHF -> UHF and real -> complex
            stability analysis.
        return_status: bool
            Whether to return `stable_i` and `stable_e`
        nroots: int
            Number of roots solved by Davidson solver
        tol: float
            Convergence tolerance for Davidson solver

    Returns:
        If return_status is False (default), the return value includes
        two set of orbitals, which are more close to the stable condition.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.

        Else, another two boolean variables (indicating current status:
        stable or unstable) are returned.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.
    '''
    mo_i = mo_e = None
    if return_status:
        stable_i = stable_e = None
        if internal:
            mo_i, stable_i = rhf_internal(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        if external:
            mo_e, stable_e = rhf_external(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        return mo_i, mo_e, stable_i, stable_e
    else:
        if internal:
            mo_i = rhf_internal(mf, verbose=verbose, nroots=nroots, tol=tol)
        if external:
            mo_e = rhf_external(mf, verbose=verbose, nroots=nroots, tol=tol)
        return mo_i, mo_e

def uhf_stability(mf, internal=True, external=False, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    '''
    Stability analysis for UHF/UKS method.

    Args:
        mf : UHF or UKS object

    Kwargs:
        internal : bool
            Internal stability, within the UHF space.
        external : bool
            External stability. Including the UHF -> GHF and real -> complex
            stability analysis.
        return_status: bool
            Whether to return `stable_i` and `stable_e`
        nroots: int
            Number of roots solved by Davidson solver
        tol: float
            Convergence tolerance for Davidson solver

    Returns:
        If return_status is False (default), the return value includes
        two set of orbitals, which are more close to the stable condition.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.

        Else, another two boolean variables (indicating current status:
        stable or unstable) are returned.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.
    '''
    mo_i = mo_e = None
    if return_status:
        stable_i = stable_e = None
        if internal:
            mo_i, stable_i = uhf_internal(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        if external:
            mo_e, stable_e = uhf_external(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        return mo_i, mo_e, stable_i, stable_e
    else:
        if internal:
            mo_i = uhf_internal(mf, verbose=verbose, nroots=nroots, tol=tol)
        if external:
            mo_e = uhf_external(mf, verbose=verbose, nroots=nroots, tol=tol)
        return mo_i, mo_e

def rohf_stability(mf, internal=True, external=False, verbose=None, return_status=False,
                   nroots=STAB_NROOTS, tol=1e-4):
    '''
    Stability analysis for ROHF/ROKS method.

    Args:
        mf : ROHF or ROKS object

    Kwargs:
        internal : bool
            Internal stability, within the RHF space.
        external : bool
            External stability. It is not available in current version.
        return_status: bool
            Whether to return `stable_i` and `stable_e`
        nroots: int
            Number of roots solved by Davidson solver
        tol: float
            Convergence tolerance for Davidson solver

    Returns:
        If return_status is False (default), the return value includes
        two set of orbitals, which are more close to the stable condition.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.

        Else, another two boolean variables (indicating current status:
        stable or unstable) are returned.
        The first corresponds to the internal stability
        and the second corresponds to the external stability.
    '''
    mo_i = mo_e = None
    if return_status:
        stable_i = stable_e = None
        if internal:
            mo_i, stable_i = rohf_internal(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        if external:
            mo_e, stable_e = rohf_external(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        return mo_i, mo_e, stable_i, stable_e
    else:
        if internal:
            mo_i = rohf_internal(mf, verbose=verbose, nroots=nroots, tol=tol)
        if external:
            mo_e = rohf_external(mf, verbose=verbose, nroots=nroots, tol=tol)
        return mo_i, mo_e

def is_complex(mf):
    if mf.mo_coeff.dtype == numpy.float64:
        return False
    else:
        dm = mf.make_rdm1()
        return abs(dm.imag).max() > 1e-6

def ghf_stability(mf, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    '''
    Stability analysis for GHF/GKS method.
    For real GHF/GKS, internal and real2complex stability analysis are performed,
    but currently only the mo (and stable) of internal analysis is returned.
    For complex GHF/GKS, internal stability analysis is performed.

    Args:
        mf : GHF or GKS object

    Kwargs:
        return_status: bool
            Whether to return `stable_i` and `stable_e`
        nroots: int
            Number of roots solved by Davidson solver
        tol: float
            Convergence tolerance for Davidson solver

    Returns:
        If return_status is False (default), the return value includes
        one set of orbitals, which is more close to the stable condition.

        Else, another one boolean variable (indicating current status:
        stable or unstable) are returned.
    '''
    mo_i = None
    if return_status:
        stable_i = None
        if is_complex(mf):
            mo_i, stable_i = ghf_complex(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        else:
            mo_i, stable_i = ghf_real(mf, verbose=verbose, return_status=True, nroots=nroots, tol=tol)
        return mo_i, stable_i
    else:
        if is_complex(mf):
            mo_i = ghf_complex(mf, verbose=verbose, nroots=nroots, tol=tol)
        else:
            mo_i = ghf_real(mf, verbose=verbose, nroots=nroots, tol=tol)
        return mo_i


def dhf_stability(mf, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    '''
    Stability analysis for DHF/DKS method.

    Args:
        mf : DHF or DKS object

    Kwargs:
        return_status: bool
            Whether to return `stable`
        nroots: int
            Number of roots solved by Davidson solver
        tol: float
            Convergence tolerance for Davidson solver

    Returns:
        If return_status is False (default), the return value includes
        a new set of orbitals, which are more close to the stable condition.

        Else, another one boolean variable (indicating current status:
        stable or unstable) is returned.
    '''
    log = logger.new_logger(mf, verbose)
    g, hop, hdiag = newton_ah.gen_g_hop_dhf(mf, mf.mo_coeff, mf.mo_occ)
    hdiag *= 2
    stable = True
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    def hessian_x(x): # See comments in function rhf_internal
        return hop(x).real * 2

    x0 = numpy.zeros_like(g)
    x0[g!=0] = 1. / hdiag[g!=0]
    x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, verbose=log, nroots=nroots)
    if e < -1e-5:
        log.note(f'{mf.__class__} wavefunction has an internal instability')
        mo = _rotate_mo(mf.mo_coeff, mf.mo_occ, v)
        stable = False
    else:
        log.note(f'{mf.__class__} wavefunction is stable in the internal '
                 'stability analysis')
        mo = mf.mo_coeff
    if return_status:
        return mo, stable
    else:
        return mo

def rhf_internal(mf, with_symmetry=True, verbose=None, return_status=False,
                 nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    g, hop, hdiag = newton_ah.gen_g_hop_rhf(mf, mf.mo_coeff, mf.mo_occ,
                                            with_symmetry=with_symmetry)
    hdiag *= 2
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    # The results of hop(x) corresponds to a displacement that reduces
    # gradients g.  It is the vir-occ block of the matrix vector product
    # (Hessian*x). The occ-vir block equals to x2.T.conj(). The overall
    # Hessian for internal reotation is x2 + x2.T.conj(). This is
    # the reason we apply (.real * 2) below
    def hessian_x(x):
        return hop(x).real * 2

    x0 = numpy.zeros_like(g)
    x0[g!=0] = 1. / hdiag[g!=0]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('rhf_internal: lowest eigs of H = %s', e)
    if nroots != 1:
        e, v = e[0], v[0]
    stable = not (e < -1e-5)
    dump_status(log, stable, f'{mf.__class__}', 'internal')
    if stable:
        mo = mf.mo_coeff
    else:
        mo = _rotate_mo(mf.mo_coeff, mf.mo_occ, v)
    if return_status:
        return mo, stable
    else:
        return mo

def _rotate_mo(mo_coeff, mo_occ, dx):
    dr = hf.unpack_uniq_var(dx, mo_occ)
    u = newton_ah.expmat(dr)
    return numpy.dot(mo_coeff, u)

def _gen_hop_rhf_external(mf, with_symmetry=True, verbose=None):
    mol = mf.mol
    mo_coeff = mf.mo_coeff
    mo_occ = mf.mo_occ
    occidx = numpy.where(mo_occ==2)[0]
    viridx = numpy.where(mo_occ==0)[0]
    nocc = len(occidx)
    nvir = len(viridx)
    orbv = mo_coeff[:,viridx]
    orbo = mo_coeff[:,occidx]

    if with_symmetry and mol.symmetry:
        orbsym = hf_symm.get_orbsym(mol, mo_coeff)
        sym_forbid = orbsym[viridx].reshape(-1,1) != orbsym[occidx]

    h1e = mf.get_hcore()
    dm0 = mf.make_rdm1(mo_coeff, mo_occ)
    fock_ao = h1e + mf.get_veff(mol, dm0)
    fock = reduce(numpy.dot, (mo_coeff.conj().T, fock_ao, mo_coeff))
    foo = fock[occidx[:,None],occidx]
    fvv = fock[viridx[:,None],viridx]

    hdiag = fvv.diagonal().reshape(-1,1) - foo.diagonal()
    if with_symmetry and mol.symmetry:
        hdiag[sym_forbid] = 0
    hdiag = hdiag.ravel()

    vrespz = mf.gen_response(singlet=None, hermi=2)
    def hop_real2complex(x1):
        x1 = x1.reshape(nvir,nocc)
        if with_symmetry and mol.symmetry:
            x1 = x1.copy()
            x1[sym_forbid] = 0
        x2 = numpy.einsum('ps,sq->pq', fvv, x1)
        x2-= numpy.einsum('ps,rp->rs', foo, x1)

        d1 = reduce(numpy.dot, (orbv, x1*2, orbo.conj().T))
        dm1 = d1 - d1.conj().T
# No Coulomb and fxc contribution for anti-hermitian DM
        v1 = vrespz(dm1)
        x2 += reduce(numpy.dot, (orbv.conj().T, v1, orbo))
        if with_symmetry and mol.symmetry:
            x2[sym_forbid] = 0
        return x2.ravel()

    vresp1 = mf.gen_response(singlet=False, hermi=1)
    def hop_rhf2uhf(x1):
        # See also rhf.TDA triplet excitation
        x1 = x1.reshape(nvir,nocc)
        if with_symmetry and mol.symmetry:
            x1 = x1.copy()
            x1[sym_forbid] = 0
        x2 = numpy.einsum('ps,sq->pq', fvv, x1)
        x2-= numpy.einsum('ps,rp->rs', foo, x1)

        d1 = reduce(numpy.dot, (orbv, x1*2, orbo.conj().T))
        dm1 = d1 + d1.conj().T
        v1ao = vresp1(dm1)
        x2 += reduce(numpy.dot, (orbv.conj().T, v1ao, orbo))
        if with_symmetry and mol.symmetry:
            x2[sym_forbid] = 0
        return x2.real.ravel()

    return hop_real2complex, hdiag, hop_rhf2uhf, hdiag


def rhf_external(mf, with_symmetry=True, verbose=None, return_status=False,
                 nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    hop1, hdiag1, hop2, hdiag2 = _gen_hop_rhf_external(mf, with_symmetry)

    def precond(dx, e, x0):
        hdiagd = hdiag1 - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = numpy.zeros_like(hdiag1)
    x0[hdiag1>1e-5] = 1. / hdiag1[hdiag1>1e-5]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag1)] = 1
    e1, v1 = lib.davidson(hop1, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('rhf_real2complex: lowest eigs of H = %s', e1)
    if nroots != 1:
        e1, v1 = e1[0], v1[0]
    stable1 = not (e1 < -1e-5)
    dump_status(log, stable1, f'{mf.__class__}', 'real -> complex')

    def precond(dx, e, x0):
        hdiagd = hdiag2 - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = v1
    e3, v3 = lib.davidson(hop2, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('rhf_external: lowest eigs of H = %s', e3)
    if nroots != 1:
        e3, v3 = e3[0], v3[0]
    stable = not (e3 < -1e-5)
    dump_status(log, stable, f'{mf.__class__}', 'RHF/RKS -> UHF/UKS')
    if stable:
        mo = (mf.mo_coeff, mf.mo_coeff)
    else:
        mo = (_rotate_mo(mf.mo_coeff, mf.mo_occ, v3), mf.mo_coeff)
    if return_status:
        return mo, stable
    else:
        return mo

def rohf_internal(mf, with_symmetry=True, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    g, hop, hdiag = newton_ah.gen_g_hop_rohf(mf, mf.mo_coeff, mf.mo_occ,
                                             with_symmetry=with_symmetry)
    hdiag *= 2
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    def hessian_x(x): # See comments in function rhf_internal
        return hop(x).real * 2

    x0 = numpy.zeros_like(g)
    x0[g!=0] = 1. / hdiag[g!=0]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('rohf_internal: lowest eigs of H = %s', e)
    if nroots != 1:
        e, v = e[0], v[0]
    stable = not (e < -1e-5)
    dump_status(log, stable, f'{mf.__class__}', 'internal')
    if stable:
        mo = mf.mo_coeff
    else:
        mo = _rotate_mo(mf.mo_coeff, mf.mo_occ, v)
    if return_status:
        return mo, stable
    else:
        return mo

def rohf_external(mf, with_symmetry=True, verbose=None, return_status=False,
                  nroots=STAB_NROOTS, tol=1e-4):
    raise NotImplementedError

def uhf_internal(mf, with_symmetry=True, verbose=None, return_status=False,
                 nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    g, hop, hdiag = newton_ah.gen_g_hop_uhf(mf, mf.mo_coeff, mf.mo_occ,
                                            with_symmetry=with_symmetry)
    hdiag *= 2
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    def hessian_x(x): # See comments in function rhf_internal
        return hop(x).real * 2

    x0 = numpy.zeros_like(g)
    x0[g!=0] = 1. / hdiag[g!=0]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('uhf_internal: lowest eigs of H = %s', e)
    if nroots != 1:
        e, v = e[0], v[0]
    stable = not (e < -1e-5)
    dump_status(log, stable, f'{mf.__class__}', 'internal')
    if stable:
        mo = mf.mo_coeff
    else:
        nocca = numpy.count_nonzero(mf.mo_occ[0]> 0)
        nvira = numpy.count_nonzero(mf.mo_occ[0]==0)
        mo = (_rotate_mo(mf.mo_coeff[0], mf.mo_occ[0], v[:nocca*nvira]),
              _rotate_mo(mf.mo_coeff[1], mf.mo_occ[1], v[nocca*nvira:]))
    if return_status:
        return mo, stable
    else:
        return mo

def _gen_hop_uhf_external(mf, with_symmetry=True, verbose=None):
    mol = mf.mol
    mo_coeff = mf.mo_coeff
    mo_occ = mf.mo_occ
    occidxa = numpy.where(mo_occ[0]>0)[0]
    occidxb = numpy.where(mo_occ[1]>0)[0]
    viridxa = numpy.where(mo_occ[0]==0)[0]
    viridxb = numpy.where(mo_occ[1]==0)[0]
    nocca = len(occidxa)
    noccb = len(occidxb)
    nvira = len(viridxa)
    nvirb = len(viridxb)
    orboa = mo_coeff[0][:,occidxa]
    orbob = mo_coeff[1][:,occidxb]
    orbva = mo_coeff[0][:,viridxa]
    orbvb = mo_coeff[1][:,viridxb]

    if with_symmetry and mol.symmetry:
        orbsyma, orbsymb = uhf_symm.get_orbsym(mol, mo_coeff)
        sym_forbida = orbsyma[viridxa].reshape(-1,1) != orbsyma[occidxa]
        sym_forbidb = orbsymb[viridxb].reshape(-1,1) != orbsymb[occidxb]
        sym_forbid1 = numpy.hstack((sym_forbida.ravel(), sym_forbidb.ravel()))

    h1e = mf.get_hcore()
    dm0 = mf.make_rdm1(mo_coeff, mo_occ)
    fock_ao = h1e + mf.get_veff(mol, dm0)
    focka = reduce(numpy.dot, (mo_coeff[0].conj().T, fock_ao[0], mo_coeff[0]))
    fockb = reduce(numpy.dot, (mo_coeff[1].conj().T, fock_ao[1], mo_coeff[1]))
    fooa = focka[occidxa[:,None],occidxa]
    fvva = focka[viridxa[:,None],viridxa]
    foob = fockb[occidxb[:,None],occidxb]
    fvvb = fockb[viridxb[:,None],viridxb]

    h_diaga =(focka[viridxa,viridxa].reshape(-1,1) - focka[occidxa,occidxa])
    h_diagb =(fockb[viridxb,viridxb].reshape(-1,1) - fockb[occidxb,occidxb])
    hdiag1 = numpy.hstack((h_diaga.reshape(-1), h_diagb.reshape(-1)))
    if with_symmetry and mol.symmetry:
        hdiag1[sym_forbid1] = 0

    vrespz = mf.gen_response(with_j=False, hermi=2)
    def hop_real2complex(x1):
        if with_symmetry and mol.symmetry:
            x1 = x1.copy()
            x1[sym_forbid1] = 0
        x1a = x1[:nvira*nocca].reshape(nvira,nocca)
        x1b = x1[nvira*nocca:].reshape(nvirb,noccb)
        x2a = numpy.einsum('pr,rq->pq', fvva, x1a)
        x2a-= numpy.einsum('sq,ps->pq', fooa, x1a)
        x2b = numpy.einsum('pr,rq->pq', fvvb, x1b)
        x2b-= numpy.einsum('qs,ps->pq', foob, x1b)

        d1a = reduce(numpy.dot, (orbva, x1a, orboa.conj().T))
        d1b = reduce(numpy.dot, (orbvb, x1b, orbob.conj().T))
        dm1 = numpy.array((d1a-d1a.conj().T, d1b-d1b.conj().T))

        v1 = vrespz(dm1)
        x2a += reduce(numpy.dot, (orbva.conj().T, v1[0], orboa))
        x2b += reduce(numpy.dot, (orbvb.conj().T, v1[1], orbob))
        x2 = numpy.hstack((x2a.ravel(), x2b.ravel()))
        if with_symmetry and mol.symmetry:
            x2[sym_forbid1] = 0
        return x2

    if with_symmetry and mol.symmetry:
        orbsyma, orbsymb = uhf_symm.get_orbsym(mol, mo_coeff)
        sym_forbidab = orbsyma[viridxa].reshape(-1,1) != orbsymb[occidxb]
        sym_forbidba = orbsymb[viridxb].reshape(-1,1) != orbsyma[occidxa]
        sym_forbid2 = numpy.hstack((sym_forbidab.ravel(), sym_forbidba.ravel()))
    hdiagab = fvva.diagonal().reshape(-1,1) - foob.diagonal()
    hdiagba = fvvb.diagonal().reshape(-1,1) - fooa.diagonal()
    hdiag2 = numpy.hstack((hdiagab.ravel(), hdiagba.ravel()))
    if with_symmetry and mol.symmetry:
        hdiag2[sym_forbid2] = 0

    vresp1 = mf.gen_response(with_j=False, hermi=0)
    # Spin flip GHF solution is not considered
    def hop_uhf2ghf(x1):
        if with_symmetry and mol.symmetry:
            x1 = x1.copy()
            x1[sym_forbid2] = 0
        x1ab = x1[:nvira*noccb].reshape(nvira,noccb)
        x1ba = x1[nvira*noccb:].reshape(nvirb,nocca)
        x2ab = numpy.einsum('pr,rq->pq', fvva, x1ab)
        x2ab-= numpy.einsum('sq,ps->pq', foob, x1ab)
        x2ba = numpy.einsum('pr,rq->pq', fvvb, x1ba)
        x2ba-= numpy.einsum('qs,ps->pq', fooa, x1ba)

        d1ab = reduce(numpy.dot, (orbva, x1ab, orbob.conj().T))
        d1ba = reduce(numpy.dot, (orbvb, x1ba, orboa.conj().T))
        dm1 = numpy.array((d1ab+d1ba.conj().T, d1ba+d1ab.conj().T))
        v1 = vresp1(dm1)
        x2ab += reduce(numpy.dot, (orbva.conj().T, v1[0], orbob))
        x2ba += reduce(numpy.dot, (orbvb.conj().T, v1[1], orboa))
        x2 = numpy.hstack((x2ab.real.ravel(), x2ba.real.ravel()))
        if with_symmetry and mol.symmetry:
            x2[sym_forbid2] = 0
        return x2

    return hop_real2complex, hdiag1, hop_uhf2ghf, hdiag2


def uhf_external(mf, with_symmetry=True, verbose=None, return_status=False,
                 nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    hop1, hdiag1, hop2, hdiag2 = _gen_hop_uhf_external(mf, with_symmetry)

    def precond(dx, e, x0):
        hdiagd = hdiag1 - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = numpy.zeros_like(hdiag1)
    x0[hdiag1>1e-5] = 1. / hdiag1[hdiag1>1e-5]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag1)] = 1
    e1, v = lib.davidson(hop1, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('uhf_real2complex: lowest eigs of H = %s', e1)
    if nroots != 1:
        e1, v = e1[0], v[0]
    stable1 = not (e1 < -1e-5)
    dump_status(log, stable1, f'{mf.__class__}', 'real -> complex')

    def precond(dx, e, x0):
        hdiagd = hdiag2 - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = numpy.zeros_like(hdiag2)
    x0[hdiag2>1e-5] = 1. / hdiag2[hdiag2>1e-5]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag2)] = 1
    e3, v = lib.davidson(hop2, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('uhf_external: lowest eigs of H = %s', e3)
    if nroots != 1:
        e3, v = e3[0], v[0]
    stable = not (e3 < -1e-5)
    dump_status(log, stable, f'{mf.__class__}', 'UHF/UKS -> GHF/GKS')
    mo = scipy.linalg.block_diag(*mf.mo_coeff)
    if not stable:
        occidxa = numpy.where(mf.mo_occ[0]> 0)[0]
        viridxa = numpy.where(mf.mo_occ[0]==0)[0]
        occidxb = numpy.where(mf.mo_occ[1]> 0)[0]
        viridxb = numpy.where(mf.mo_occ[1]==0)[0]
        nocca = len(occidxa)
        nvira = len(viridxa)
        noccb = len(occidxb)
        nvirb = len(viridxb)
        nmo = nocca + nvira
        dx = numpy.zeros((nmo*2,nmo*2))
        dx[viridxa[:,None],nmo+occidxb] = v[:nvira*noccb].reshape(nvira,noccb)
        dx[nmo+viridxb[:,None],occidxa] = v[nvira*noccb:].reshape(nvirb,nocca)
        u = newton_ah.expmat(dx - dx.conj().T)
        mo = numpy.dot(mo, u)
        mo = numpy.hstack([mo[:,:nocca], mo[:,nmo:nmo+noccb],
                           mo[:,nocca:nmo], mo[:,nmo+noccb:]])
    if return_status:
        return mo, stable
    else:
        return mo

def _gen_hop_ghf_real2complex(mf, with_symmetry=True, verbose=None):
    mol = mf.mol
    mo_coeff = mf.mo_coeff
    mo_occ = mf.mo_occ
    occidx = numpy.where(mo_occ==1)[0]
    viridx = numpy.where(mo_occ==0)[0]
    nocc = len(occidx)
    nvir = len(viridx)
    orbv = mo_coeff[:,viridx]
    orbo = mo_coeff[:,occidx]

    if with_symmetry and mol.symmetry:
        orbsym = ghf_symm.get_orbsym(mol, mo_coeff)
        sym_forbid = orbsym[viridx, None] != orbsym[occidx]

    h1e = mf.get_hcore()
    dm0 = mf.make_rdm1(mo_coeff, mo_occ)
    fock_ao = mf.get_fock(h1e, dm=dm0)
    fock = reduce(numpy.dot, (mo_coeff.conj().T, fock_ao, mo_coeff))
    foo = fock[occidx[:,None],occidx]
    fvv = fock[viridx[:,None],viridx]

    hdiag = fvv.diagonal().real[:,None] - foo.diagonal().real
    if with_symmetry and mol.symmetry:
        hdiag[sym_forbid] = 0
    hdiag = hdiag.ravel()

    vrespz = mf.gen_response(#singlet=None,
                             with_j=False,
                             hermi=0)
    def hop_real2complex(x1):
        x1 = x1.reshape(nvir,nocc)
        if with_symmetry and mol.symmetry:
            x1 = x1.copy()
            x1[sym_forbid] = 0
        x2 = numpy.einsum('ps,sq->pq', fvv, x1)
        x2-= numpy.einsum('ps,rp->rs', foo, x1)

        d1 = reduce(numpy.dot, (orbv, x1, orbo.conj().T))
        dm1 = d1 - d1.conj().T
# No Coulomb and fxc contribution for anti-hermitian DM
        v1 = vrespz(dm1)
        x2 += reduce(numpy.dot, (orbv.conj().T, v1, orbo))
        if with_symmetry and mol.symmetry:
            x2[sym_forbid] = 0
        return x2.ravel()

    return hop_real2complex, hdiag

def _gen_hop_ghf_complex_internal(mf, with_symmetry=True, verbose=None):
    mol = mf.mol
    mo_coeff = mf.mo_coeff
    mo_energy = mf.mo_energy
    mo_occ = mf.mo_occ
    nao, nmo = mo_coeff.shape
    occidx = numpy.where(mo_occ == 1)[0]
    viridx = numpy.where(mo_occ == 0)[0]
    nocc = len(occidx)
    nvir = len(viridx)
    orbv = mo_coeff[:,viridx]
    orbo = mo_coeff[:,occidx]

    if with_symmetry and mol.symmetry:
        orbsym = ghf_symm.get_orbsym(mol, mo_coeff)
        sym_forbid = orbsym[viridx] != orbsym[occidx]

    foo = numpy.diag(mo_energy[occidx])
    fvv = numpy.diag(mo_energy[viridx])

    hdiag = fvv.diagonal() - foo.diagonal()[:,None]
    if with_symmetry and mol.symmetry:
        hdiag[sym_forbid] = 0
    hdiag = numpy.hstack((hdiag.ravel(), hdiag.ravel().conj()))

    mo_coeff = numpy.asarray(numpy.hstack((orbo,orbv)), order='F')
    vresp = mf.gen_response(hermi=0)

    def hop(x1):
        x1 = numpy.asarray(x1).reshape(2,nocc,nvir)
        if with_symmetry and mol.symmetry:
            # shape(nz,2,nocc,nvir): 2 ~ X,Y
            x1 = numpy.copy(x1)
            x1[:,sym_forbid] = 0

        xs, ys = x1
        # dms = AX + BY
        dms  = lib.einsum('ov,qv,po->pq', xs, orbv.conj(), orbo)
        dms += lib.einsum('ov,pv,qo->pq', ys, orbv, orbo.conj())

        v1ao = vresp(dms)
        v1ov = lib.einsum('pq,po,qv->ov', v1ao, orbo.conj(), orbv)
        v1vo = lib.einsum('pq,qo,pv->ov', v1ao, orbo, orbv.conj())
        v1ov += lib.einsum('qs,sp->qp', xs, fvv)  # AX
        v1ov -= lib.einsum('pr,sp->sr', xs, foo)  # AX
        v1vo += lib.einsum('qs,sp->qp', ys, fvv.conj())  # (A*)Y
        v1vo -= lib.einsum('pr,sp->sr', ys, foo.conj())  # (A*)Y

        if with_symmetry and mol.symmetry:
            v1ov[:,sym_forbid] = 0
            v1vo[:,sym_forbid] = 0

        # (AX, (-A*)Y)
        #nz = x1.shape[0]
        hx = numpy.hstack((v1ov.ravel(), v1vo.ravel()))
        return hx

    return hop, hdiag

def ghf_real(mf, with_symmetry=True, verbose=None, return_status=False,
             nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    #with_symmetry = True
    g, hop, hdiag = newton_ah.gen_g_hop_ghf(mf, mf.mo_coeff, mf.mo_occ)
    hdiag *= 2
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    def hessian_x(x): # See comments in function rhf_internal
        return hop(x).real * 2

    x0 = numpy.zeros_like(g)
    x0[g!=0] = 1. / hdiag[g!=0]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('ghf_real_internal: lowest eigs of H = %s', e)
    if nroots != 1:
        e, v = e[0], v[0]
    stable = not (e < -1e-5)
    dump_status(log, stable, f'{mf.__class__} (real)', 'internal')
    if stable:
        mo = mf.mo_coeff
    else:
        mo = _rotate_mo(mf.mo_coeff, mf.mo_occ, v)

    hop_r2c, hdiag_r2c = _gen_hop_ghf_real2complex(mf, with_symmetry=with_symmetry)
    def precond(dx, e, x0):
        hdiagd = hdiag_r2c - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = numpy.zeros_like(hdiag_r2c)
    x0[hdiag_r2c>1e-5] = 1. / hdiag_r2c[hdiag_r2c>1e-5]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag_r2c)] = 1
    e2, v2 = lib.davidson(hop_r2c, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('ghf_real2complex: lowest eigs of H = %s', e2)
    if nroots != 1:
        e2, v = e2[0], v[0]
    stable_r2c = not (e2 < -1e-5)
    dump_status(log, stable_r2c, f'{mf.__class__} (real)', 'real -> complex')
    if return_status:
        return mo, stable
    else:
        return mo

def ghf_complex(mf, verbose=None, return_status=False,
                nroots=STAB_NROOTS, tol=1e-4):
    log = logger.new_logger(mf, verbose)
    with_symmetry = True
    hop, hdiag = _gen_hop_ghf_complex_internal(mf)
    def precond(dx, e, x0):
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd)<1e-8] = 1e-8
        return dx/hdiagd
    x0 = numpy.zeros_like(hdiag)
    x0[hdiag>1e-5] = 1. / hdiag[hdiag>1e-5]
    if not with_symmetry:  # allow to break point group symmetry
        x0[numpy.argmin(hdiag)] = 1
    e, v = lib.davidson(hop, x0, precond, tol=tol, verbose=log, nroots=nroots)
    log.info('ghf_complex_internal: lowest eigs of H = %s', e)
    if nroots != 1:
        e, v = e[0], v[0]
    stable = not (e < -1e-5)
    dump_status(log, stable, f'{mf.__class__} (complex)', 'internal')
    if stable:
        mo = mf.mo_coeff
    else:
        mo = _rotate_mo(mf.mo_coeff, mf.mo_occ, v)

    if return_status:
        return mo, stable
    else:
        return mo

if __name__ == '__main__':
    from pyscf import gto, scf, dft
    mol = gto.M(atom='O 0 0 0; O 0 0 1.2222', basis='631g*')
    mf = scf.RHF(mol).run()
    rhf_stability(mf, True, True, verbose=4)

    mf = dft.RKS(mol).run(level_shift=.2)
    rhf_stability(mf, True, True, verbose=4)

    mf = scf.UHF(mol).run()
    mo1 = uhf_stability(mf, True, True, verbose=4)[0]

    mf = scf.newton(mf).run(mo1, mf.mo_occ)
    uhf_stability(mf, True, False, verbose=4)
    mf = scf.newton(scf.UHF(mol)).run()
    uhf_stability(mf, True, False, verbose=4)

    mol.spin = 2
    mf = scf.UHF(mol).run()
    uhf_stability(mf, True, True, verbose=4)

    mf = dft.UKS(mol).run()
    uhf_stability(mf, True, True, verbose=4)

    mol = gto.M(atom='''
O1
O2  1  1.2227
O3  1  1.2227  2  114.0451
                ''', basis = '631g*')
    mf = scf.RHF(mol).run()
    rhf_stability(mf, True, True, verbose=4)

    mf = scf.UHF(mol).run()
    mo1 = uhf_stability(mf, True, True, verbose=4)[0]

    mf = scf.newton(scf.UHF(mol)).run()
    uhf_stability(mf, True, True, verbose=4)

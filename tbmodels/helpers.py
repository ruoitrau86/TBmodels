#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>
# Date:    04.06.2015 14:26:21 CEST
# File:    helpers.py

"""
This module contains a helper function to create a list of hoppings from a given matrix (:meth:`matrix_to_hop`), and functions for encoding / decoding to JSON - compatible datastructures (:meth:`encode`, :meth:`decode`).
"""

import numbers
import contextlib
from functools import singledispatch
from collections.abc import Iterable

import numpy as np
from fsc.export import export

from ._ptools import sparse_matrix as sp

from ._tb_model import Model

@export
def matrix_to_hop(mat, orbitals=None, R=(0, 0, 0), multiplier=1.):
    r"""
    Turns a square matrix into a series of hopping terms.

    :param mat: The matrix to be converted.

    :param orbitals:    Indices of the orbitals that make up the basis w.r.t. which the matrix is defined. By default (``orbitals=None``), the first ``len(mat)`` orbitals are used.
    :type orbitals:     list

    :param R:   Lattice vector for all the hopping terms.
    :type R:    list

    :param multiplier:  Multiplicative constant for the hopping strength.
    :type multiplier: float / complex
    """
    if orbitals is None:
        orbitals = list(range(len(mat)))
    hop = []
    for i, row in enumerate(mat):
        for j, x in enumerate(row):
            hop.append([multiplier * x, orbitals[i], orbitals[j], np.array(R, dtype=int)])
    return hop

#-------------------------------ENCODING--------------------------------#

@export
@singledispatch
def encode(obj):
    """
    Encodes TBmodels types into JSON / msgpack - compatible types. This can be used for the ``default`` keyword with the builtin :py:func:`json.dump` and :py:func:`json.dumps`, or with the corresponding functions in :py:mod:`msgpack`.
    
    .. code::
    
        import json
        import tbmodels
        
        model = ... # create a tbmodels.Model object
        
        with open('file.json', 'w') as f:
            json.dump(model, f, default=tbmodels.helpers.encode)
    
    .. note ::
        
        It is recommended to use :meth:`.Model.to_json` or :meth:`.Model.to_json_file` unless the encode function is needed explicitly.
    """
    raise TypeError('cannot JSONify {} object {}'.format(type(obj), obj))

@encode.register(np.bool_)
def _(obj):
    return bool(obj)

@encode.register(numbers.Integral)
def _(obj):
    return int(obj)

@encode.register(numbers.Real)
def _(obj):
    return float(obj)
    
@encode.register(numbers.Complex)
def _(obj):
    return dict(__complex__=True, real=encode(obj.real), imag=encode(obj.imag))

@encode.register(Iterable)
def _(obj):
    return list(obj)

@encode.register(Model)
def _(obj):
    return dict(
        __tb_model__=True,
        uc=obj.uc,
        occ=obj.occ,
        size=obj.size,
        dim=obj.dim,
        pos=obj.pos,
        hop=_encode_hoppings(obj.hop)
    )

def _encode_hoppings(hoppings):
    return dict(
        __hoppings__=[
            (R, (mat.data, mat.indices, mat.indptr), mat.shape)
            for R, mat in hoppings.items()
        ]
    )

#-------------------------------DECODING--------------------------------#

def _decode_tb_model(obj):
    del obj['__tb_model__']
    return Model(contains_cc=False, **obj)
    
def _decode_hoppings(obj):
    return {
        tuple(R): sp.csr(tuple(mat), shape=shape)
        for R, mat, shape in obj['__hoppings__']
    }
    
def _decode_complex(obj):
    return complex(obj['real'], obj['imag'])

@export
def decode(dct):
    """
    Decodes JSON / msgpack - compatible types into TBmodels types. This can be used for the ``object_hook`` keyword with the builtin :py:func:`json.load` and :py:func:`json.loads`, or with the corresponding functions in :py:mod:`msgpack`.
    
    .. code::
    
        import json
        import tbmodels
        
        with open('file.json', 'r') as f:
            json.load(f, object_hook=tbmodels.helpers.decode)
    
    .. note ::
        
        It is recommended to use :meth:`.Model.from_json` or :meth:`.Model.from_json_file` unless the decode function is needed explicitly.
    """
    with contextlib.suppress(AttributeError):
        dct = {k.decode('utf-8'): v for k, v in dct.items()}
    special_markers = [key for key in dct.keys() if key.startswith('__')]
    if len(special_markers) == 1:
        name = special_markers[0].strip('__')
        return globals()['_decode_' + name](dct)
    else:
        return dct

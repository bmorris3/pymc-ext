# -*- coding: utf-8 -*-

from __future__ import division, print_function

import numpy as np


def balance_companion_matrix(companion_matrix):
    diag = np.array(np.diag(companion_matrix))
    companion_matrix[np.diag_indices_from(companion_matrix)] = 0.0
    degree = len(diag)

    # gamma <= 1 controls how much a change in the scaling has to
    # lower the 1-norm of the companion matrix to be accepted.
    #
    # gamma = 1 seems to lead to cycles (numerical issues?), so
    # we set it slightly lower.
    gamma = 0.9

    scaling_has_changed = True
    while scaling_has_changed:
        scaling_has_changed = False

        for i in range(degree):
            row_norm = np.sum(np.abs(companion_matrix[i]))
            col_norm = np.sum(np.abs(companion_matrix[:, i]))

            # Decompose row_norm/col_norm into mantissa * 2^exponent,
            # where 0.5 <= mantissa < 1. Discard mantissa (return value
            # of frexp), as only the exponent is needed.
            _, exponent = np.frexp(row_norm / col_norm)
            exponent = exponent // 2

            if exponent != 0:
                scaled_col_norm = np.ldexp(col_norm, exponent)
                scaled_row_norm = np.ldexp(row_norm, -exponent)
                if scaled_col_norm+scaled_row_norm < gamma*(col_norm+row_norm):
                    # Accept the new scaling. (Multiplication by powers of
                    # 2 should not introduce rounding errors (ignoring
                    # non-normalized numbers and over- or underflow))
                    scaling_has_changed = True
                    companion_matrix[i] *= np.ldexp(1.0, -exponent)
                    companion_matrix[:, i] *= np.ldexp(1.0, exponent)

    companion_matrix[np.diag_indices_from(companion_matrix)] = diag
    return companion_matrix


def solve_companion_matrix(poly):
    poly = np.atleast_1d(poly)
    comp = np.eye(len(poly) - 1, k=-1)
    comp[:, -1] = -poly[:-1] / poly[-1]
    return np.linalg.eigvals(balance_companion_matrix(comp))


def get_quadratic(a, e, cosw, sinw, cosi, sini):
    e2 = e*e
    e2mo = e2 - 1
    return (
        (e2*cosw*cosw - 1),
        2*e2*sinw*cosw/sini,
        (e2mo - e2*cosw*cosw)/(sini*sini),
        -2*a*e*e2mo*cosw,
        -2*a*e*e2mo*sinw/sini,
        a**2*e2mo*e2mo,
    )


def get_quartic(A, B, C, D, E, F, T, L):
    A2 = A*A
    B2 = B*B
    C2 = C*C
    D2 = D*D
    E2 = E*E
    F2 = F*F
    T2 = T*T
    L2 = L*L
    return (
        C2*L2*L2 + 2*C*F*L2*T - E2*L2*T + F2*T2,
        -2*T*(B*E*L2 - C*D*L2 - D*F*T),
        2*A*C*L2*T + 2*A*F*T2 - B2*L2*T - 2*C2*L2 - 2*C*F*T + D2*T2 + E2*T,
        2*T*(A*D*T + B*E - C*D),
        A2*T2 - 2*A*C*T + B2*T + C2,
    )


def get_roots_general(a, e, omega, i, L, tol=1e-8):
    cosw = np.cos(omega)
    sinw = np.sin(omega)
    cosi = np.cos(i)
    sini = np.sin(i)

    f0 = 2 * np.arctan2(cosw, 1 + sinw)

    quad = get_quadratic(a, e, cosw, sinw, cosi, sini)
    A, B, C, D, E, F = quad
    T = cosi / sini
    T *= T
    quartic = get_quartic(A, B, C, D, E, F, T, L)

    roots = solve_companion_matrix(quartic)
    roots = roots[np.argsort(np.real(roots))]

    # Deal with multiplicity
    roots[0] = roots[:2][np.argmin(np.abs(np.imag(roots[:2])))]
    roots[1] = roots[2:][::-1][np.argmin(np.abs(np.imag(roots[2:])[::-1]))]
    roots = roots[:2]

    # Only select real roots
    roots = np.clip(np.real(roots[np.abs(np.imag(roots)) < tol]), -L, L)
    if len(roots) < 2:
        return np.empty(0)

    angles = []
    for x in roots:
        b0 = A*x*x + D*x + F
        b1 = B*x + E
        b2 = C
        z1 = -0.5 * b1 / b2
        arg = b1*b1 - 4*b0*b2
        if arg < 0:
            continue
        z2 = 0.5 * np.sqrt(arg) / b2
        for sgn in [-1, 1]:
            z = z1 + sgn * z2
            if z > 0:
                continue

            x0 = x*cosw + z*sinw/sini
            y0 = -x*sinw + z*cosw/sini
            angle = np.arctan2(y0, x0) - np.pi
            if angle < -np.pi:
                angle += 2*np.pi
            angles.append(angle - f0)

    # Wrap the roots properly to span the transit
    angles = np.sort(angles)
    if len(angles) == 2:
        if np.all(angles > 0):
            angles = np.array([angles[1] - 2*np.pi, angles[0]])
        if np.all(angles < 0):
            angles = np.array([angles[1], angles[0] + 2*np.pi])
    else:
        angles = np.array([-np.pi, np.pi])

    return angles + f0
"""Independent scalar oracle SOURCE; execute only in reviewed learner operation.

Category masses (erfc) and piecewise Gaussian density quadrature independently
form the complete arithmetic. Neither calls ndtr or the candidate predictor.
Quadrature estimates/convergence are empirical checks, not rigorous enclosures.
"""
import math


def moments(case,action):
    mean=math.fsum([case['alpha'],*(x*b for x,b in zip(case['x'],case['b'])),
                   (action-.5)*case['tau'],case['rho']**case['h']*case['e_T']])
    variance=math.fsum([case['s_Q']**2,
        *(case['s_e']**2*case['rho']**(2*j) for j in range(case['h']))])
    return mean,math.sqrt(variance)


def cdf(z):
    return .5*math.erfc(-z/math.sqrt(2))


def interval_mass(lo,hi):
    # Work in the smaller tail when both endpoints are positive.
    if lo>=0:return .5*(math.erfc(lo/math.sqrt(2))-math.erfc(hi/math.sqrt(2)))
    return .5*(math.erfc(-hi/math.sqrt(2))-math.erfc(-lo/math.sqrt(2)))


def exact_q(value):
    # Same specified ties-to-even scaled rounding, independently implemented.
    return round(min(10.,max(0.,value))*1000)/1000


def categories(mean,sd):
    if sd==0:return exact_q(mean)
    # Interior category probabilities, plus clipped upper terminal category.
    terms=[10.*.5*math.erfc((9.9995-mean)/(sd*math.sqrt(2)))]
    for k in range(1,10000):
        lo=((k-.5)/1000-mean)/sd;hi=((k+.5)/1000-mean)/sd
        terms.append((k/1000)*interval_mass(lo,hi))
    return math.fsum(terms)


def quadrature(mean,sd,tolerance):
    from scipy.integrate import quad
    if sd==0:return exact_q(mean),0.
    # Truncate only the ORACLE integration at |Z|=12. Outside contribution
    # bounded by 10*P(|Z|>12). It is not a predictor approximation.
    values=[];errors=[]
    density=lambda z:math.exp(-z*z/2)/math.sqrt(2*math.pi)
    for k in range(1,10001):
        lo=max(-12.,((k-.5)/1000-mean)/sd)
        hi=12. if k==10000 else min(12.,((k+.5)/1000-mean)/sd)
        if lo>=hi:continue
        value,error=quad(density,lo,hi,epsabs=tolerance/10001,epsrel=tolerance,limit=40)
        values.append((k/1000)*value);errors.append((k/1000)*error)
    return math.fsum(values),math.fsum(errors)+10*math.erfc(12/math.sqrt(2))


def full_case(case):
    output=[]
    for action in (0,1):
        mean,sd=moments(case,action)
        value=categories(mean,sd)
        coarse,error=quadrature(mean,sd,1e-12)
        fine,fine_error=quadrature(mean,sd,1e-13)
        if max(abs(value-coarse),abs(value-fine),abs(coarse-fine),error,fine_error)>1e-10:
            raise ValueError('independent reference convergence/error target failed')
        output.append(dict(mean=mean,sd=sd,quality=value,quadrature=fine,
                           estimated_error=fine_error,convergence=abs(coarse-fine)))
    cells=[]
    for delta0 in (-.5,0.,.5):
        for delta1 in (-.5,0.,.5):
            a=[]
            for action,delta in ((0,delta0),(1,delta1)):
                rate=case['r'+str(action)];m=output[action]['quality']
                a.append(math.fsum([(1-rate)*m,rate*min(10.,max(0.,m+delta))]))
            cells.append(dict(delta0=delta0,delta1=delta1,action0=a[0],action1=a[1],gap=a[1]-a[0]))
    return dict(actions=output,cells=cells)

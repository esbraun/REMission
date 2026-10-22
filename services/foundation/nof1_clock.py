"""Noon boundaries for the single accepted fictional 72-night template."""

BLOCKS=8
TREATMENT_NIGHTS=7
WASHOUT_NIGHTS=2
BLOCK_DAYS=TREATMENT_NIGHTS+WASHOUT_NIGHTS
TOTAL_DAYS=BLOCKS*BLOCK_DAYS
REVIEW_DAYS=(36,72)


def boundaries_at(day):
    """Review precedes any next block draw at the same noon."""
    if not 0<=day<=TOTAL_DAYS:
        return ()
    result=[]
    if day in REVIEW_DAYS:
        result.append('review')
    if day==TOTAL_DAYS:
        result.append('complete')
    elif day%BLOCK_DAYS==0:
        result.append('block_start')
    elif day%BLOCK_DAYS==TREATMENT_NIGHTS:
        result.append('washout_start')
    return tuple(result)


def phase_at(day):
    if day<0:
        raise ValueError('protocol has not started')
    if day>=TOTAL_DAYS:
        return dict(phase='review',block=BLOCKS,protocol_day=day)
    return dict(phase='block' if day%BLOCK_DAYS<TREATMENT_NIGHTS else 'washout',
                block=day//BLOCK_DAYS+1,protocol_day=day)

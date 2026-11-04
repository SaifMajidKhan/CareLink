"""Isolated synthetic model lab: never accepts patient identifiers or records."""
import hashlib, json, math
from pathlib import Path

def example_prediction():
    root=Path(__file__).resolve().parent.parent/'research'
    raw=(root/'model_parameters_SYNTHETIC.json').read_bytes()
    model=json.loads(raw)
    if model.get('is_synthetic') is not True: raise ValueError('Synthetic provenance required')
    # Fixed invented example only; no link to a patient or an alert rule.
    sample=[28,18,6,4,4,2,0]
    z=model['intercept']+sum(c*(v-m)/s for c,v,m,s in zip(model['coefficients'],sample,model['scaler_mean'],model['scaler_scale'],strict=True))
    score=1/(1+math.exp(-z))
    report=json.loads((root/'validation_report.json').read_text())
    return {'is_synthetic':True,'sample':dict(zip(model['feature_order'],sample,strict=True)),
            'score':score,'threshold':model['threshold'],'class_at_threshold':int(score>=model['threshold']),
            'model_sha256':hashlib.sha256(raw).hexdigest(),'validation':report['metrics'],
            'warning':'Fixed invented example only. Not a patient prediction, calibrated clinical probability, or alert trigger.'}

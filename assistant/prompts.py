"""Response styles independent of the answer-generation backend."""
import re

def classify_intent(question):
    if re.search(r'\b(recommend|suggest|find|activities|programs|groups)\b', question.lower()):
        return 'recommendation'
    if re.search(r'\b(how|why|explain)\b', question.lower()):
        return 'explanation'
    return 'factual'

def choose_template(intent):
    return {'recommendation': 'Here are matching options from our sources.',
            'explanation': 'Here is what our sources say.',
            'factual': 'I found this information in our sources.'}.get(intent, 'Here is what our sources say.')

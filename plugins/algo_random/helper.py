import random


def get_random(length: int, specified_min: float = 0):
    if length < 5:
        min_value = 0.5
        max_value = 0.8
    elif length < 10:
        min_value = 0.6
        max_value = 0.9
    else:
        min_value = 0.7
        max_value = 1.0

    if specified_min:
        return random.uniform(min_value, max_value)
    else:
        return random.uniform(specified_min, max_value)


length_to_value = {}

for i in range(50):
    length_to_value[i] = {
        "accuracy": get_random(i),
        "precision": get_random(i),
        "recall": get_random(i),
        "probability": get_random(i, 0.6)
    }


def get_scores(train, test, model, length) -> dict:
    # get the scores
    return {
        "accuracy": length_to_value[length]["accuracy"],
        "precision": length_to_value[length]["precision"],
        "recall": length_to_value[length]["recall"],
        "probability": length_to_value[length]["probability"]
    }


def get_negative_alarm(predictions, threshold) -> bool:
    # get the negative alarm
    return random.random() > 0.7

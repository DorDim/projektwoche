from dataclasses import dataclass

from server.models import AlertRule, HardwareSnapshot


@dataclass
class RuleEvaluation:
    rule: AlertRule
    metric_value: float | None
    triggered: bool
    message: str | None


def _min_disk_free_percent(snapshot: HardwareSnapshot) -> float | None:
    disks = snapshot.disks or []
    if not disks:
        return None
    values = [disk.get("free_percent") for disk in disks if disk.get("free_percent") is not None]
    if not values:
        return None
    return float(min(values))


def metric_value_for_rule(snapshot: HardwareSnapshot, metric: str) -> float | None:
    if metric == "disk_free_percent_min":
        return _min_disk_free_percent(snapshot)
    if metric == "uptime_seconds":
        return float(snapshot.uptime_seconds) if snapshot.uptime_seconds is not None else None
    return None


def evaluate_rule(rule: AlertRule, snapshot: HardwareSnapshot) -> RuleEvaluation:
    value = metric_value_for_rule(snapshot, rule.metric)
    if value is None:
        return RuleEvaluation(rule=rule, metric_value=None, triggered=False, message=None)

    if rule.comparator == "lt":
        triggered = value < rule.threshold
        relation = "unter"
    elif rule.comparator == "gt":
        triggered = value > rule.threshold
        relation = "über"
    else:
        triggered = False
        relation = "ungültig"

    message = None
    if triggered:
        message = (
            f"Regel '{rule.name}' ausgelöst: {rule.metric}={value:.2f} "
            f"liegt {relation} Grenzwert {rule.threshold:.2f}"
        )

    return RuleEvaluation(rule=rule, metric_value=value, triggered=triggered, message=message)

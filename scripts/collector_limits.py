"""Conservative, persisted volume stages; never reactivate a rejected source."""
from statistics import median


def mode(attempt):
    request = attempt.get('request', {})
    data = request.get('data', {})
    return request.get('url', '') + (':named' if data.get('mmcNm') else ':unfiltered')


def limits(state, policy, source_name, now):
    source = state['sources'][source_name]
    setting = policy['sources'].get(source_name, {})
    base = {'requests_per_24h': setting.get('requests_per_24h', policy['requests_per_24h']),
            'requests_per_run': setting.get('requests_per_run', policy['requests_per_run']),
            'interval_seconds': setting.get('interval_seconds', policy['interval_seconds']),
            'stage': 'fixed'}
    if source['status'] in ('blocked', 'needs_review'):
        return {**base, 'requests_per_run': 0, 'stage': 'stopped'}
    config = policy.get('volume_ramp', {})
    if not config.get('enabled') or source_name not in config['sources']:
        return base
    ramp = source.setdefault('volume_ramp', {'stage': 'pilot', 'started_at': now, 'clean_since': now})
    recent = [a for a in state['attempts'] if a['source'] == source_name and max(ramp['clean_since'], now-config['clean_seconds']) <= a['at'] <= now and
              a.get('status') == 'done' and not a.get('health_signal')]
    required = config['minimum_valid_responses'] if ramp['stage'] == 'pilot' else config['backoff_minimum_valid_responses']
    if ramp['stage'] in ('pilot', 'backoff') and source['status'] == 'active' and \
            now-ramp['clean_since'] >= config['clean_seconds'] and len(recent) >= required:
        ramp['stage'] = 'promoted' if ramp['stage'] == 'pilot' else 'pilot'
        ramp['changed_at'] = now
        ramp['clean_since'] = now
        recent = []
    values = config['stages'][ramp['stage']]
    return {**base, **values, 'stage': ramp['stage'], 'clean_since': ramp['clean_since'],
            'valid_responses_in_clean_window': len(recent),
            'earliest_review_at': ramp['clean_since']+config['clean_seconds']}


def run_limit(state, policy, now):
    values = [limits(state, policy, source, now)['requests_per_run'] for source in state['sources']]
    return max(values, default=0)


def observe(state, policy, source_name, attempt, now):
    config = policy.get('volume_ramp', {})
    if not config.get('enabled') or source_name not in config['sources']:
        return
    source = state['sources'][source_name]
    ramp = source['volume_ramp']
    status = attempt['status']
    if status != 'done':
        attempt['health_signal'] = status
        ramp.update(stage='backoff', clean_since=now, changed_at=now, slow_streak=0)
        # Unknown response contracts require review, not another target query.
        if status == 'needs_review':
            source.update(status='needs_review', reason='Collection response contract requires review')
        return
    comparable = [a['network_duration_seconds'] for a in state['attempts'] if
                  a is not attempt and a['source'] == source_name and a.get('status') == 'done' and
                  not a.get('health_signal') and a.get('network_duration_seconds') is not None and mode(a) == mode(attempt)]
    slow = len(comparable) >= config['latency_minimum_samples'] and \
        attempt.get('network_duration_seconds', 0) > max(config['latency_floor_seconds'],
             config['latency_multiplier'] * median(comparable[-20:]))
    if slow:
        attempt['health_signal'] = 'slow_response'
        ramp['clean_since'] = now
        ramp['slow_streak'] = ramp.get('slow_streak', 0)+1
        # One unusual payload holds promotion; repeated slow responses reduce
        # load. A single slow response also cancels an existing promotion.
        if ramp['stage'] == 'promoted':
            ramp.update(stage='pilot', changed_at=now)
        if ramp['slow_streak'] >= 2:
            ramp.update(stage='backoff', changed_at=now)
    else:
        ramp['slow_streak'] = 0


def snapshot(state, policy, now):
    result = {source: limits(state, policy, source, now) for source in state['sources']}
    state['effective_collection_limits'] = result
    return result

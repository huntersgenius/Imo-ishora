import { useEffect, useState } from 'react';
import { getHealth } from '../lib/api';
import { config } from '../lib/config';
import type { HealthResponse } from '../lib/types';

// Compact brand header with a quiet backend readiness indicator.
export function BrandHeader() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let active = true;
    void getHealth().then((h) => {
      if (active) {
        setHealth(h);
        setChecked(true);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const dotClass = !checked
    ? 'brand__health-dot'
    : health
      ? health.playable_clips > 0
        ? 'brand__health-dot brand__health-dot--ok'
        : 'brand__health-dot brand__health-dot--warn'
      : 'brand__health-dot';

  const healthLabel = !checked
    ? 'ulanmoqda'
    : health
      ? `${health.playable_clips} klip tayyor`
      : 'oflayn';

  return (
    <header className="brand">
      <div className="brand__mark">
        <span className="brand__name">
          IMO<span className="brand__dot">·</span>ISHORA
        </span>
        <span className="brand__tag">{config.demoLabel}</span>
      </div>
      <div className="brand__health" title="Backend holati">
        <span className={dotClass} aria-hidden="true" />
        <span>{healthLabel}</span>
      </div>
    </header>
  );
}

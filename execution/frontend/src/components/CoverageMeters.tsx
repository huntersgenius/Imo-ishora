import { motion } from 'motion/react';
import { formatPercent } from '../lib/format';

interface Props {
  languageCoverage: number;
  videoCoverage: number;
}

// Two-axis coverage: linguistic (known words) vs video (playable clips).
// Both are shown so partial coverage reads as honest, not broken.
export function CoverageMeters({ languageCoverage, videoCoverage }: Props) {
  return (
    <div className="coverage">
      <Meter
        label="Til qamrovi"
        value={languageCoverage}
        variant="lang"
        hint="Lug'atda topilgan so'zlar"
      />
      <Meter
        label="Video qamrovi"
        value={videoCoverage}
        variant="video"
        hint="Tayyor video kliplar"
      />
    </div>
  );
}

function Meter({
  label,
  value,
  variant,
  hint,
}: {
  label: string;
  value: number;
  variant: 'lang' | 'video';
  hint: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="meter">
      <div className="meter__head">
        <span className="meter__label" title={hint}>
          {label}
        </span>
        <span className="meter__value">{formatPercent(clamped)}</span>
      </div>
      <div
        className="meter__track"
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <motion.div
          className={`meter__fill meter__fill--${variant}`}
          initial={{ width: 0 }}
          animate={{ width: `${clamped}%` }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  );
}

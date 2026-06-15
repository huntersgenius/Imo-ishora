import { useStore } from '../lib/store';
import { WordChip } from '../components/WordChip';
import { CoverageMeters } from '../components/CoverageMeters';

// Phases reflect real backend job status without faking FFmpeg internals.
const PHASES = [
  { key: 'analyze', label: 'Matn tahlili' },
  { key: 'lookup', label: 'Kliplarni topish' },
  { key: 'synthesis', label: 'Video yig‘ish' },
  { key: 'delivery', label: 'R2 yetkazib berish' },
] as const;

// Map backend job status -> how far along the phase list we are.
function phaseProgress(status: string | null): number {
  switch (status) {
    case 'queued':
      return 1; // analysis done, waiting to process
    case 'processing':
      return 2; // lookup + synthesis underway
    case 'completed':
      return 4;
    default:
      return 1;
  }
}

export function ProcessingView() {
  const normalizedText = useStore((s) => s.normalizedText);
  const words = useStore((s) => s.words);
  const languageCoverage = useStore((s) => s.languageCoverage);
  const videoCoverage = useStore((s) => s.videoCoverage);
  const jobStatus = useStore((s) => s.jobStatus);

  const progress = phaseProgress(jobStatus);

  return (
    <section className="panel processing" aria-labelledby="proc-title">
      <div>
        <span className="section-title" id="proc-title">
          Tayyorlanmoqda
        </span>
        <p className="processing__accepted">{normalizedText}</p>
      </div>

      <div className="processing__block">
        <span className="section-title">So‘zlar</span>
        <div className="chips">
          {words.map((word, i) => (
            <WordChip key={`${word.source_text}-${i}`} word={word} index={i} />
          ))}
        </div>
      </div>

      <CoverageMeters
        languageCoverage={languageCoverage}
        videoCoverage={videoCoverage}
      />

      <div className="processing__block">
        <span className="section-title">Jarayon</span>
        <ol className="phases">
          {PHASES.map((phase, i) => {
            const done = i < progress - 1;
            const active = i === progress - 1;
            const cls = done
              ? 'phase phase--done'
              : active
                ? 'phase phase--active'
                : 'phase';
            return (
              <li className={cls} key={phase.key}>
                <span className="phase__icon" aria-hidden="true">
                  {done ? '✓' : active ? '' : i + 1}
                </span>
                <span>{phase.label}</span>
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

import { useStore } from '../lib/store';
import { VideoPlayer } from '../components/VideoPlayer';
import { CoverageMeters } from '../components/CoverageMeters';
import { formatDuration } from '../lib/format';

// Video-centric result. Warnings for partial coverage are shown, never hidden.
export function ResultView() {
  const videoUrl = useStore((s) => s.videoUrl);
  const output = useStore((s) => s.output);
  const warnings = useStore((s) => s.warnings);
  const foundCount = useStore((s) => s.foundCount);
  const playableCount = useStore((s) => s.playableCount);
  const skippedCount = useStore((s) => s.skippedCount);
  const languageCoverage = useStore((s) => s.languageCoverage);
  const videoCoverage = useStore((s) => s.videoCoverage);
  const reset = useStore((s) => s.reset);

  return (
    <section className="result" aria-labelledby="result-title">
      <div className="success-banner">
        <span className="success-banner__ring" aria-hidden="true">
          ✓
        </span>
        <span id="result-title">Video tayyor</span>
      </div>

      {videoUrl ? (
        <VideoPlayer src={videoUrl} />
      ) : (
        <p>Video manzili topilmadi.</p>
      )}

      <div className="summary-row" aria-label="Natija xulosasi">
        <span className="summary-row__item">
          <span className="summary-row__num">{playableCount}</span> klip yig‘ildi
        </span>
        <span className="summary-row__item">
          <span className="summary-row__num">{foundCount}</span> so‘z tanildi
        </span>
        {skippedCount > 0 && (
          <span className="summary-row__item">
            <span className="summary-row__num">{skippedCount}</span> birikma
          </span>
        )}
        {output?.duration_seconds != null && (
          <span className="summary-row__item">
            <span className="summary-row__num">
              {formatDuration(output.duration_seconds)}
            </span>{' '}
            davomiylik
          </span>
        )}
      </div>

      <CoverageMeters
        languageCoverage={languageCoverage}
        videoCoverage={videoCoverage}
      />

      {warnings.length > 0 && (
        <div className="warnings" role="status">
          {warnings.map((w, i) => (
            <span className="warnings__item" key={i}>
              <span aria-hidden="true">•</span>
              {w}
            </span>
          ))}
        </div>
      )}

      <div className="btn-row">
        <button className="btn btn--primary" onClick={reset}>
          Yangi matn
        </button>
        {videoUrl && (
          <a
            className="btn btn--ghost"
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Videoni ochish
          </a>
        )}
      </div>
    </section>
  );
}

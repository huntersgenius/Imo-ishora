import { useStore } from '../lib/store';
import type { ErrorCode } from '../lib/types';

interface ErrorPresentation {
  title: string;
  action: string;
}

// Each known error maps to a calm title and one clear next action. The backend
// already provides a user-safe message; we add a heading and action verb.
const PRESENTATION: Record<ErrorCode, ErrorPresentation> = {
  input_validation: { title: 'Matnni tekshiring', action: 'Tahrirlash' },
  no_supported_words: { title: 'So‘zlar topilmadi', action: 'Boshqa matn' },
  no_playable_clips: { title: 'Kliplar hali tayyor emas', action: 'Boshqa matn' },
  r2_configuration: { title: 'Server sozlamasi', action: 'Qayta urinish' },
  r2_object_missing: { title: 'Video topilmadi', action: 'Qayta urinish' },
  video_processing: { title: 'Video yig‘ishda xatolik', action: 'Qayta urinish' },
  processing_timeout: { title: 'Vaqt tugadi', action: 'Qayta urinish' },
  internal: { title: 'Kutilmagan xatolik', action: 'Qayta urinish' },
  unknown_job: { title: 'Job topilmadi', action: 'Boshidan' },
  network: { title: 'Ulanish uzildi', action: 'Qayta urinish' },
  client_timeout: { title: 'Juda uzoq davom etdi', action: 'Qayta urinish' },
};

export function ErrorView() {
  const error = useStore((s) => s.error);
  const reset = useStore((s) => s.reset);

  const code: ErrorCode = error?.code ?? 'internal';
  const presentation = PRESENTATION[code] ?? PRESENTATION.internal;
  const message = error?.message ?? 'Xatolik yuz berdi.';

  return (
    <section className="panel error-view" role="alert" aria-labelledby="err-title">
      <span className="error-view__icon" aria-hidden="true">
        !
      </span>
      <h2 className="error-view__title" id="err-title">
        {presentation.title}
      </h2>
      <p className="error-view__msg">{message}</p>
      <span className="error-view__code">{code}</span>
      <div className="btn-row">
        <button className="btn btn--primary" onClick={reset}>
          {presentation.action}
        </button>
      </div>
    </section>
  );
}

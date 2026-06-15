import { useMemo, useState } from 'react';
import { useStore } from '../lib/store';
import { config } from '../lib/config';
import { demoPhrases } from '../lib/demoPhrases';

// The first screen IS the tool: headline + composer + suggestions, no marketing.
export function InputView() {
  const inputText = useStore((s) => s.inputText);
  const setInputText = useStore((s) => s.setInputText);
  const submit = useStore((s) => s.submit);
  const isSubmitting = useStore((s) => s.isSubmitting);

  const [touched, setTouched] = useState(false);

  const trimmed = inputText.trim();
  const length = inputText.length;
  const over = length > config.maxInputLength;
  const empty = trimmed.length === 0;

  const counterClass = useMemo(() => {
    if (over) return 'counter counter--over';
    if (length > config.maxInputLength * 0.85) return 'counter counter--warn';
    return 'counter';
  }, [length, over]);

  const validationMsg = touched && empty
    ? 'Iltimos, biror matn kiriting.'
    : over
      ? `Matn ${config.maxInputLength} belgidan oshmasligi kerak.`
      : '';

  const canSubmit = !empty && !over && !isSubmitting;

  const onSubmit = () => {
    setTouched(true);
    if (!canSubmit) return;
    void submit(inputText);
  };

  return (
    <section className="input-view" aria-labelledby="headline">
      <div>
        <h1 className="headline" id="headline">
          O‘zbek matnini <em>jonli imo-ishora</em>ga aylantiring.
        </h1>
        <p className="headline__sub">
          Matn kiriting — tizim so‘zlarni rus imo-ishora tili belgilariga
          moslab, yagona videoga birlashtiradi.
        </p>
      </div>

      <div className="panel composer">
        <div className="composer__field">
          <label htmlFor="uz-input" className="visually-hidden">
            O‘zbek matni
          </label>
          <textarea
            id="uz-input"
            value={inputText}
            placeholder="Masalan: salom, bugun yaxshi kun"
            maxLength={config.maxInputLength + 40}
            onChange={(e) => setInputText(e.target.value)}
            onBlur={() => setTouched(true)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') onSubmit();
            }}
            aria-invalid={over || (touched && empty)}
          />
        </div>

        <div className="composer__meta">
          <span className="validation" role={validationMsg ? 'alert' : undefined}>
            {validationMsg && <span aria-hidden="true">⚠</span>}
            {validationMsg}
          </span>
          <span className={counterClass}>
            {length}/{config.maxInputLength}
          </span>
        </div>

        <div className="btn-row">
          <button
            className="btn btn--primary"
            onClick={onSubmit}
            disabled={!canSubmit}
          >
            {isSubmitting ? 'Yuborilmoqda…' : 'Imo-ishoraga aylantirish'}
          </button>
        </div>
      </div>

      <div className="suggestions">
        <span className="section-title">Namuna iboralar</span>
        <div className="suggestions__chips">
          {demoPhrases.map((phrase) => (
            <button
              key={phrase.text}
              className="suggestion"
              onClick={() => {
                setInputText(phrase.text);
                setTouched(false);
              }}
              type="button"
            >
              {phrase.text}
              <span className="suggestion__hint">{phrase.hint}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

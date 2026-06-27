"use client";

import { FormEvent, useState } from "react";

type FeedbackFormState = {
  usefulness_rating: number | null;
  confidence_rating: number | null;
  most_useful: string;
  improvement_priority: string;
  future_feature_interest: string[];
  comment: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const mostUsefulOptions = [
  ["repeat_failures", "Finding repeat failures"],
  ["maintenance_strategy_review", "Maintenance strategy review"],
  ["equipment_data_search", "Equipment/data search"],
  ["recommendations_next_actions", "Recommendations/next actions"],
  ["conversation_memory_context", "Conversation memory/context"],
  ["other", "Other"],
] as const;

const improvementOptions = [
  ["data_accuracy", "Data accuracy"],
  ["more_detailed_evidence", "More detailed evidence"],
  ["better_recommendations", "Better recommendations"],
  ["upload_import_workflow", "Upload/import workflow"],
  ["faster_responses", "Faster responses"],
  ["easier_ui", "Easier UI"],
  ["other", "Other"],
] as const;

const futureFeatureOptions = [
  ["knowledge_base", "Knowledge base"],
  [
    "configure_subagent_model_selection",
    "Configure subagent model selection",
  ],
  ["upload_data", "Upload data"],
  ["additional_subagent", "Additional subagent"],
  ["additional_tools", "Additional tools"],
] as const;

const initialFeedbackForm: FeedbackFormState = {
  usefulness_rating: null,
  confidence_rating: null,
  most_useful: "",
  improvement_priority: "",
  future_feature_interest: [],
  comment: "",
};

function RatingInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
}) {
  return (
    <fieldset className="feedback-rating-field">
      <legend>{label}</legend>
      <div className="feedback-rating-options">
        {[1, 2, 3, 4, 5].map((rating) => (
          <label key={rating}>
            <input
              checked={value === rating}
              name={label}
              onChange={() => onChange(rating)}
              type="radio"
              value={rating}
            />
            <span>{rating}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default function FeedbackSurvey({
  conversationId,
  isOpen,
  onClose,
  onDismiss,
  onSubmitted,
}: {
  conversationId?: string | null;
  isOpen: boolean;
  onClose: () => void;
  onDismiss: () => void;
  onSubmitted: () => void;
}) {
  const [form, setForm] = useState<FeedbackFormState>(initialFeedbackForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  if (!isOpen) {
    return null;
  }

  function updateField<K extends keyof FeedbackFormState>(
    field: K,
    value: FeedbackFormState[K],
  ) {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function toggleFutureFeature(feature: string) {
    setForm((currentForm) => {
      const selected = currentForm.future_feature_interest.includes(feature);
      return {
        ...currentForm,
        future_feature_interest: selected
          ? currentForm.future_feature_interest.filter((item) => item !== feature)
          : [...currentForm.future_feature_interest, feature],
      };
    });
  }

  async function submitFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!API_URL || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      const response = await fetch(`${API_URL}/feedback`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: conversationId ?? null,
          usefulness_rating: form.usefulness_rating,
          confidence_rating: form.confidence_rating,
          most_useful: form.most_useful || null,
          improvement_priority: form.improvement_priority || null,
          future_feature_interest: form.future_feature_interest,
          comment: form.comment.trim() || null,
        }),
      });

      if (response.status === 401) {
        throw new Error("Please sign in before sending feedback.");
      }

      if (!response.ok) {
        throw new Error("Feedback could not be saved.");
      }

      setForm(initialFeedbackForm);
      onSubmitted();
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Feedback could not be saved. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      aria-labelledby="feedback-survey-title"
      aria-modal="true"
      className="feedback-modal-backdrop"
      role="dialog"
    >
      <form className="feedback-modal" onSubmit={submitFeedback}>
        <div className="feedback-modal-header">
          <div>
            <p>
              1 min feedback{" "}
              <span className="feedback-optional-mark">(optional)</span>
            </p>
            <h2 id="feedback-survey-title">How is Polaris working?</h2>
          </div>
          <button
            aria-label="Close feedback survey"
            className="feedback-close-button"
            onClick={onClose}
            type="button"
          >
            x
          </button>
        </div>

        <RatingInput
          label="Overall usefulness"
          onChange={(value) => updateField("usefulness_rating", value)}
          value={form.usefulness_rating}
        />
        <RatingInput
          label="Confidence using this for reliability work"
          onChange={(value) => updateField("confidence_rating", value)}
          value={form.confidence_rating}
        />

        <label className="feedback-select-field">
          <span>What was most useful?</span>
          <select
            onChange={(event) => updateField("most_useful", event.target.value)}
            value={form.most_useful}
          >
            <option value="">Select one</option>
            {mostUsefulOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="feedback-select-field">
          <span>What should improve first?</span>
          <select
            onChange={(event) =>
              updateField("improvement_priority", event.target.value)
            }
            value={form.improvement_priority}
          >
            <option value="">Select one</option>
            {improvementOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <fieldset className="feedback-checkbox-field">
          <legend>Future features you are interested in</legend>
          <div>
            {futureFeatureOptions.map(([value, label]) => (
              <label key={value}>
                <input
                  checked={form.future_feature_interest.includes(value)}
                  onChange={() => toggleFutureFeature(value)}
                  type="checkbox"
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="feedback-comment-field">
          <span>Comment</span>
          <textarea
            maxLength={1000}
            onChange={(event) => updateField("comment", event.target.value)}
            placeholder="What would make this more useful for your work?"
            rows={3}
            value={form.comment}
          />
        </label>

        {errorMessage ? (
          <p className="feedback-error" role="alert">
            {errorMessage}
          </p>
        ) : null}

        <div className="feedback-actions">
          <button
            className="feedback-secondary-button"
            onClick={onDismiss}
            type="button"
          >
            Maybe later
          </button>
          <button
            className="feedback-primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Sending..." : "Send feedback"}
          </button>
        </div>
      </form>
    </div>
  );
}

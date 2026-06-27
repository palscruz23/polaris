"use client";

import { useState } from "react";
import FeedbackSurvey from "./FeedbackSurvey";

export default function HomeFeedbackButton() {
  const [feedbackIsOpen, setFeedbackIsOpen] = useState(false);

  return (
    <>
      <button
        className="home-footer-link home-footer-button"
        onClick={() => setFeedbackIsOpen(true)}
        type="button"
      >
        Send feedback
      </button>
      <FeedbackSurvey
        isOpen={feedbackIsOpen}
        onClose={() => setFeedbackIsOpen(false)}
        onDismiss={() => setFeedbackIsOpen(false)}
        onSubmitted={() => setFeedbackIsOpen(false)}
      />
    </>
  );
}

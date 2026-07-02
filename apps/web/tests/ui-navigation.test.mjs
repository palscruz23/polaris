import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";

const homePage = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const polarisWatchButton = readFileSync(
  new URL("../app/HomePolarisWatchButton.tsx", import.meta.url),
  "utf8",
);
const chatPage = readFileSync(
  new URL("../app/features/[slug]/AgentWorkflowChat.tsx", import.meta.url),
  "utf8",
);
const globalStyles = readFileSync(
  new URL("../app/globals.css", import.meta.url),
  "utf8",
);

test("homepage presents Polaris Watch as a distinct exploration CTA", () => {
  assert.match(polarisWatchButton, /Explore Polaris Watch/);
  assert.doesNotMatch(polarisWatchButton, /See Polaris Watch/);
  assert.match(polarisWatchButton, /button-watch/);
  assert.match(globalStyles, /\.button-watch\s*\{/);
});

test("synthetic data navigation is removed from homepage CTAs", () => {
  assert.doesNotMatch(homePage, /HomeSyntheticDataButton/);
});

test("chat header orders sign out, synthetic data, then feedback actions", () => {
  const actions = chatPage.match(
    /<div className="agent-chat-header-actions">[\s\S]*?<\/div>/,
  )?.[0];

  assert.ok(actions, "chat header actions should exist");
  assert.match(actions, /href="\/view-existing-data"/);
  assert.match(actions, /View synthetic data/);
  assert.match(actions, /agent-chat-data/);

  const signOutIndex = actions.indexOf("Sign out");
  const syntheticDataIndex = actions.indexOf("View synthetic data");
  const feedbackIndex = actions.indexOf("Feedback");

  assert.ok(signOutIndex > -1, "sign out action should be present");
  assert.ok(syntheticDataIndex > -1, "synthetic data action should be present");
  assert.ok(feedbackIndex > -1, "feedback action should be present");
  assert.ok(signOutIndex < syntheticDataIndex);
  assert.ok(syntheticDataIndex < feedbackIndex);
});

// The stories of the demo, one per file of this folder. The demo starts with a
// random story and tells the next one in every new round; the first step of a
// story offers all of them. A story is { title, steps }. Its steps have the
// fields of the steps of the tutorial (tour-steps.js), but name a place of
// prerequisites.js instead of a CSS selector:
//   at    the place the hint points to; its page is the page of the step unless `url` says more
//   act   "click" or ["fill", value] act on that place; a function does anything else
//   full  true: the step needs the full view although its place does not
// The texts are told by the AI that built the app, to an experienced data
// scientist, and are written to be listened to: the story title, then the text
// of each step; the titles of the steps are only shown.

import { AT } from "./prerequisites.js";
import lungs from "./1-lungs.js";
import older from "./2-older.js";
import heart from "./3-heart.js";
import pancreas from "./4-pancreas.js";
import blood from "./5-blood.js";
import making from "./6-making.js";

// A step of a story in the form of tour.js: target, page and view from its place.
function resolve({ at, act, full, ...step }) {
  const place = at ? AT[at] : null;
  const target = place?.sel;
  return {
    ...step, at, target,
    url: step.url ?? place?.page,
    advanced: Boolean(full || place?.full),
    act: act === "click" ? (t) => t.click(target) : Array.isArray(act) ? (t) => t.fill(target, act[1]) : act,
  };
}

export const STORIES = [lungs, older, heart, pancreas, blood, making]
  .map((story) => ({ ...story, steps: story.steps.map(resolve) }));

// Multi-user ratings: empty page -> several people rate -> a state we
// can predict exactly.
//
// Every expected number is computed here from the formula, not read back
// from the app, so a change to the aggregation breaks the test instead of
// silently agreeing with itself.

import { expect, test } from '@playwright/test';
import { asUser, bandFor, bayes, mean, TestApp } from './fixtures.js';

// Each test uses its own combinations and seeds whatever it needs, so
// any one of them can be run alone with `-g` and still mean something.
const KATSUO = ['Katsuobushi', 'Maple_butter'];
const MARMITE = ['Marmite', 'Tsampa'];
const DOENJANG = ['Doenjang', 'Sticky_toffee_pudding'];
const OATCAKE = ['Maple_butter', 'Oatcake'];
const HARISSA = ['Harissa', 'Welsh_rarebit'];

const keyOf = (foods) => [...foods].sort().join('|');

// Rate a combination through the UI: open the form, drag the slider to
// an exact value, submit.
const cardFor = (page, foods) =>
  page.locator('.card', {
    has: page.locator(`h3 a:text-is("${foods[0].replace(/_/g, ' ')}")`),
  });

async function rate(page, foods, score, notes = '') {
  // The first rating moves a combination out of Proposed, so later
  // raters have to look somewhere it is still listed.
  await page.click('.tabs button:has-text("All")');
  const card = cardFor(page, foods);
  await expect(card).toBeVisible();
  await card.locator('.link', { hasText: /tried this|change rating/ }).click();
  // Set the range input directly: dragging is pixel-approximate and this
  // test cares about the exact number.
  await card.locator("input[type='range']").fill(String(score));
  await expect(card.locator('.slider-value')).toHaveText(String(score));
  if (notes) await card.locator(".trial-form input[type='text']").first().fill(notes);
  await card.locator('.submit').click();
  await expect(card.locator('.trial-form')).toHaveCount(0);
}

test.describe('ratings aggregate across users', () => {
  let app;

  test.beforeAll(async () => {
    app = await TestApp.start();
  });

  test.afterAll(async () => {
    await app?.stop();
  });

  test('empty ledger shows nothing', async ({ page }) => {
    await page.goto(app.origin);
    await expect(page.locator('.card')).toHaveCount(0);
    await expect(page.locator('main')).toContainText('Nothing here yet');
  });

  test('four users rating one combination reach a predicted state', async ({
    browser,
  }) => {
    await app.propose(KATSUO, {
      rationale: 'inosinate against caramel',
      groups: [
        'Meals.style.List_of_smoked_foods',
        'Meals.Sweets.List_of_foods_made_from_maple',
      ],
    });

    const scores = { alice: 90, bob: 80, carol: 85, dave: 95 };
    for (const [name, score] of Object.entries(scores)) {
      const { context, page } = await asUser(browser, app.origin, name);
      await rate(page, KATSUO, score, `${name} says so`);
      await context.close();
    }

    const values = Object.values(scores); // 90 80 85 95
    const expectedMean = mean(values); // 87.5
    const expectedBayes = bayes(values); // (150+350)/7 = 71.43

    const state = await app.state(keyOf(KATSUO));
    expect(state.n_trials).toBe(4);
    expect(state.mean_score).toBeCloseTo(expectedMean, 6);
    expect(state.bayes_score).toBeCloseTo(expectedBayes, 6);
    expect(state.min_score).toBe(80);
    expect(state.max_score).toBe(95);
    expect(state.status).toBe(bandFor(expectedMean)); // tried_good

    // And the UI shows that same number, rounded.
    const { context, page } = await asUser(browser, app.origin, 'reader');
    await page.click('.tabs button:has-text("Tried")');
    const card = cardFor(page, KATSUO);
    await expect(card.locator('.rating-number')).toHaveText(
      String(Math.round(expectedMean))
    );
    await expect(card.locator('.rating-n')).toHaveText('n=4');
    await expect(card.locator('.badge')).toHaveText('good');
    await expect(card.locator('.rating')).toHaveClass(/rating-good/);
    await context.close();
  });

  test('a lone rave ranks below a well-tested favourite', async ({
    browser,
  }) => {
    // One perfect score against four in the eighties. A raw mean would
    // put the lone rave on top, which is the bug shrinkage prevents.
    await app.propose(MARMITE, { rationale: 'shared pyrazines' });
    await app.propose(OATCAKE, { rationale: 'toasted-grain register' });
    const tested = [88, 80, 85, 90];
    for (const [i, score] of tested.entries()) {
      await app.rate(OATCAKE, `taster${i}`, score);
    }

    const { context, page } = await asUser(browser, app.origin, 'erin');
    await rate(page, MARMITE, 100);
    await context.close();

    const marmite = await app.state(keyOf(MARMITE));
    const oatcake = await app.state(keyOf(OATCAKE));

    expect(marmite.mean_score).toBe(100); // higher raw mean...
    expect(marmite.mean_score).toBeGreaterThan(oatcake.mean_score);
    expect(marmite.bayes_score).toBeCloseTo(bayes([100]), 6); // 62.5
    expect(oatcake.bayes_score).toBeCloseTo(bayes(tested), 6); // 72.0
    expect(marmite.bayes_score).toBeLessThan(oatcake.bayes_score); // ...ranks lower

    // The list, ordered by rating, agrees.
    const ranked = await app.combos('?order=rating');
    const order = ranked.map((c) => c.combo_key);
    expect(order.indexOf(keyOf(OATCAKE))).toBeLessThan(
      order.indexOf(keyOf(MARMITE))
    );

    // A single enthusiastic rating still *reads* as good, though: the
    // band comes from the raw mean, only the ranking is shrunk.
    expect(marmite.status).toBe('tried_good');
  });

  test('disagreement lands in the middle and is visible as a spread', async ({
    browser,
  }) => {
    await app.propose(DOENJANG, { rationale: 'miso caramel precedent' });
    for (const [name, score] of [
      ['frank', 95],
      ['grace', 10],
    ]) {
      const { context, page } = await asUser(browser, app.origin, name);
      await rate(page, DOENJANG, score);
      await context.close();
    }

    const state = await app.state(keyOf(DOENJANG));
    expect(state.mean_score).toBeCloseTo(mean([95, 10]), 6); // 52.5
    expect(state.status).toBe('tried_mixed');
    expect(state.min_score).toBe(10);
    expect(state.max_score).toBe(95);

    const { context, page } = await asUser(browser, app.origin, 'reader2');
    await page.click('.tabs button:has-text("Tried")');
    const card = cardFor(page, DOENJANG);
    await expect(card.locator('.badge')).toHaveText('mixed');
    await expect(card.locator('.meta')).toContainText('spread 10–95');
    await context.close();
  });

  test('re-rating replaces that person, and keeps the history', async ({
    browser,
  }) => {
    await app.propose(HARISSA, { rationale: 'caraway finds the beer' });
    await app.rate(HARISSA, 'mel', 90);
    await app.rate(HARISSA, 'nia', 80);

    const { context, page } = await asUser(browser, app.origin, 'mel');
    await rate(page, HARISSA, 20); // mel turns on it: 90 -> 20

    const state = await app.state(keyOf(HARISSA));
    expect(state.n_trials).toBe(2); // still two people, not three
    expect(state.mean_score).toBeCloseTo(mean([20, 80]), 6); // 50

    // The log kept both of mel's ratings -- nothing was overwritten.
    const melTrials = state.events.filter(
      (e) => e.kind === 'trial' && e.actor === 'mel'
    );
    expect(melTrials.map((e) => e.payload.score)).toEqual([90, 20]);
    await context.close();
  });

  test('a disliked combination becomes settled', async ({ browser }) => {
    const SPROUTS = ['Brussels_sprout', 'Custard'];
    await app.propose(SPROUTS, { rationale: 'deliberately bad' });
    for (const [name, score] of [
      ['hank', 15],
      ['iris', 25],
    ]) {
      const { context, page } = await asUser(browser, app.origin, name);
      await rate(page, SPROUTS, score);
      await context.close();
    }
    const state = await app.state(keyOf(SPROUTS));
    expect(state.mean_score).toBeCloseTo(20, 6);
    expect(state.status).toBe('tried_bad');
    // 'settled' is what stops search.py re-offering it.
    expect(state.settled).toBe(true);
  });
});

test.describe('facets', () => {
  let app;

  test.beforeAll(async () => {
    app = await TestApp.start();
    await app.propose(DOENJANG, {
      rationale: 'miso caramel precedent',
      groups: [
        'Meals.Asia.List_of_Korean_dishes',
        'Meals.origin.List_of_British_desserts',
      ],
    });
    await app.propose(['Ricotta', 'Vincotto'], {
      groups: [
        'Meals.style.List_of_smoked_foods',
        'Meals.Sweets.List_of_syrups',
      ],
    });
    app.tag();
  });

  test.afterAll(async () => {
    await app?.stop();
  });

  test('tags are derived from the source lists', async () => {
    const [combo] = await app.combos('?tag=cuisine:korean');
    expect(combo.foods).toEqual(DOENJANG.sort());
    expect(combo.tags).toEqual(
      expect.arrayContaining([
        'course:dessert',
        'cuisine:british',
        'cuisine:korean',
      ])
    );
  });

  test('filters intersect rather than union', async () => {
    expect(await app.combos('?tag=cuisine:korean&tag=course:dessert')).toHaveLength(1);
    // Korean AND smoked matches nothing, even though each matches one.
    expect(await app.combos('?tag=cuisine:korean&tag=technique:smoked')).toHaveLength(0);
    expect(await app.combos('?tag=technique:smoked')).toHaveLength(1);
  });

  test('clicking a chip filters the list, and clearing restores it', async ({
    browser,
  }) => {
    const { context, page } = await asUser(browser, app.origin, 'jo');
    await expect(page.locator('.card')).toHaveCount(2);

    await page.locator('.facets .tag', { hasText: 'korean' }).click();
    await expect(page.locator('.card')).toHaveCount(1);
    await expect(page.locator('.card h3')).toContainText('Doenjang');

    // Adding a contradictory facet empties it, with an explanation.
    await page.locator('.facets .tag', { hasText: 'smoked' }).click();
    await expect(page.locator('.card')).toHaveCount(0);
    await expect(page.locator('main')).toContainText('Nothing matches');

    await page.locator('.clear').click();
    await expect(page.locator('.card')).toHaveCount(2);
    await context.close();
  });

  test('an unknown facet is rejected', async () => {
    const res = await fetch(`${app.origin}/api/combos?tag=nonsense:x`);
    expect(res.status).toBe(400);
    expect((await res.json()).error).toContain('Unknown facet');
  });
});

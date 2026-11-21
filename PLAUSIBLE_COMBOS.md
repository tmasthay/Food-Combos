# Plausible combinations

A worked pass over the current database: 224 scraped Wikipedia lists, 13,733
distinct foods. Everything below is reproducible from the repo — each entry
names the narrowing that surfaces it, so you can re-run the search and see the
rest of that pool.

The rule I applied: keep a pair only if I can name the *mechanism* — a reason
the two would work, not just the fact that both are food. Pairs that are the
same idea twice, or that are already a standard dish, are listed at the bottom
as rejects.

## Smoke against sour dairy

**Arbroath smokie + Rømmegrøt**

```
python search.py combos --slot smoked --slot porridge \
    --require-any "arbroath" --require-any "rømmegrøt"
```

Hot-smoked haddock flaked into Norwegian sour-cream porridge. The porridge is
already fat and lactic; smoked white fish is salt, smoke and gelatine with no
sweetness of its own. This is kedgeree's logic with the rice swapped for a
grain that brings its own acid. Nordic on both sides, which is why it reads as
plausible rather than arbitrary.

**Smoked plum + Shrikhand**

```
python search.py combos --slot smoked --slot '*yogurt*' \
    --require-any "smoked plum" --require-any "shrikhand"
```

Shrikhand is strained yogurt with saffron and cardamom. Smoked plum supplies
the one thing it lacks — a bitter, tarry top note — and stone fruit and
cardamom already belong together. The risk is the smoke swamping the saffron,
so it wants to be a spoonful of plum, not a layer.

## Umami against sweet

**Katsuobushi + Maple butter**

```
python search.py combos --slot smoked --slot maple \
    --require-any "katsuobushi" --require-any "maple butter"
```

The best pair in this pass. Maple butter is maple syrup whipped to a spread;
its character is sotolon and caramel. Katsuobushi is dried, smoked, fermented
bonito — nearly pure inosinate plus smoke. Salt-plus-inosinate against caramel
is the same move as bacon with maple, with the pork's fat removed and the smoke
intensified. On toast, with butter underneath.

**Marmite + Tsampa**

```
python search.py combos --slot '*food_pastes*' --slot porridge \
    --require-any "marmite" --require-any "tsampa"
```

Tsampa is roasted barley flour, usually worked into tea and butter. Roasted
barley and yeast extract are both heavy in Maillard pyrazines, so the flavours
run parallel rather than fighting; the yeast extract supplies the salt and
glutamate the flour has none of. This is Vegemite-on-toast transposed onto a
grain that is already roasted. Use a quarter of what you think.

**Doenjang + Sticky toffee pudding**

```
python search.py combos --slot '*korean*' --slot '*british_desserts*' \
    --require-any "doenjang" --require-any "sticky toffee"
```

Sticky toffee pudding is date, treacle and butter — it is already halfway to a
savoury glaze. Fermented soybean paste in the toffee sauce would push it the
rest of the way: salt and funk cutting a sauce that is otherwise relentless.
The precedent is miso caramel, which works; doenjang is coarser and more
assertive, so this is the riskiest entry here.

## Acid against fat

**Pickled walnuts + Blue Stilton**

```
python search.py combos --slot pickled --slot '*english_cheeses*' \
    --require-any "pickled walnut" --require-any "stilton"
```

Included as a control, not a discovery: this is a real British pairing, and the
fact that the method lands on it from two unrelated Wikipedia lists is the
argument that the method works. Tannic, sweet-sour, malt-vinegared walnut
against ammoniated blue fat.

**Umeboshi + Kaya toast**

```
python search.py combos --slot pickled --slot toast \
    --require-any "umeboshi" --require-any "kaya"
```

Kaya toast is coconut-and-egg jam on toast, and in Singapore it is already
eaten with soy sauce and white pepper on soft eggs alongside — the savoury
counterweight is part of the dish. Umeboshi does that job with acid instead of
salt alone. Sweet coconut custard, sour salted plum, charred bread.

**Beni shōga + Porchetta**

```
python search.py combos --slot pickled --slot '*pork*' \
    --require-any "beni" --require-any "porchetta"
```

Porchetta is fennel, fat and crackling and traditionally wants a sharp pickle;
beni shōga is ginger pickled in umezu, so it brings acid *and* a warm aromatic
that sits on top of fennel rather than clashing with it. The strongest "swap
one component of a known dish" candidate in the set.

**Harissa + Welsh rarebit**

```
python search.py combos --slot '*condiments*' --slot toast \
    --require-any "harissa" --require-any "welsh rarebit"
```

Rarebit is cheese, mustard, beer and Worcestershire — a sauce built on heat and
funk. Harissa substitutes for the mustard with capsaicin, caraway and roasted
pepper sweetness. Nearly a free swap; worth doing because the caraway finds the
beer.

## Fat against sugar syrup

**Smoked ricotta + Vincotto**

```
python search.py combos --slot smoked --slot '*syrups*' \
    --require-any "ricotta" --require-any "vincotto"
```

Vincotto is cooked grape must — sweet, sharp, faintly balsamic. Fresh ricotta
with honey is a standard plate; smoked ricotta is firmer, saltier and drier, so
it needs a syrup with acid rather than straight honey. Both are southern
Italian, which is why this one is almost certainly already eaten somewhere in
Puglia.

**Maple butter + Oatcake**

```
python search.py combos --slot '*maple*' --slot '*crackers*' \
    --require-any "maple butter" --require-any "oatcake"
```

The quiet one. Oatcakes are dry, salty and faintly bitter and exist to carry
fat; maple butter is fat-free sugar that behaves like fat. Oat and maple share
a toasted-grain register, so this is less a collision than a completion. Add
blue cheese and it stops being a two-item combination.

**Birch syrup + Lox**

```
python search.py combos --slot '*syrups*' --slot smoked \
    --require-any "birch syrup" --require-any "lox"
```

Birch syrup is not maple — it is savoury, mineral, almost molasses-bitter, and
it is used in Alaska and Finland as a glaze for fish. Against cold-cured salmon
it would do what a sweet mustard-dill sauce does, with the sugar pulled back.
The one caution is that lox is already salt-forward, so this is a brushing, not
a pour.

## Nut paste against starch dessert

**Tahini + Warabimochi**

```
python search.py combos --slot '*food_pastes*' --slot '*japanese_desserts*' \
    --require-any "tahini" --require-any "warabimochi"
```

Warabimochi is bracken-starch jelly served under kinako — roasted soy flour.
Kinako and tahini occupy the same roasted-seed register, but tahini brings fat
and bitterness the flour cannot. With kuromitsu over the top it becomes a halva
argument made with mochi.

## Rejected, and why

The method produces a lot of these, and discarding them is most of the work:

- **Chocolate-covered prune + Chocolate truffle** — the same idea twice. This
  is what `shared_token_penalty` and `distinct_groups` exist to suppress.
- **Pickled cucumber + Corned beef** — already a sandwich.
- **Espresso rub + Pork ribs** — already on `List_of_coffee_dishes`; the
  database contains the answer, so it is not a discovery.
- **Peanut paste + Brazil** — `List_of_doughnut_varieties` has a country column,
  and the scraper cannot tell a country from a doughnut. Noise, not a combo.
- **Paprika + Tsampa** — plausible-sounding and empty: paprika is an
  ingredient, not a thing you combine with a porridge. Watch for entries that
  are *components* rather than dishes; `List_of_smoked_foods` is full of them
  (`Liquid_smoke`, `Smoked_salt`, `Merkén`).
- **Apple + Avocado toast** — "Apple" is on `List_of_pickled_foods` because
  pickled apple exists, but the entry is the fruit's article. Single-word
  generic entries are usually too vague to judge.

## How to continue this

Pick a mechanism first, then write the narrowing that explores it — not the
other way round. `--rank-distinct` pushes the same-idea-twice pairs down, and
`--per-group` keeps `List_of_desserts` (1,355 entries) from drowning a 14-entry
list. Quote the seed so a pool can be revisited.

```
python search.py combos --slot smoked --slot '*cheeses*' \
    --per-group 40 --rank-distinct -n 20 --seed 7 --urls
```

"""`build_rows` decides everything that lands in the spreadsheet, so this is where
the filtering and the value rungs get pinned. No client, no network, no key - just
fetched data in, rows out.

Row layout, used throughout:
    0 Account Name  1 Character Name  2 Amount  3 Item ID
    4 Item Name     5 Value           6 Source  7 Description
"""

import unittest

from .harness import (ACCOUNT_NAME, BANK, CHARACTERS, CURRENCIES, ECTO, ETERNITY,
                      MATERIALS, MINI, SHARED, SHINY, SHINY_NAME, SPINEGUARD,
                      TRANSFORM, WALLET, extractor, items_dict, prices_dict)

ACCOUNT, CHARACTER, AMOUNT, ITEM_ID, ITEM_NAME, VALUE, SOURCE, DESCRIPTION = range(8)

build_rows = extractor.build_rows
item_value = extractor.item_value
format_coin = extractor.format_coin
wallet_first = extractor.wallet_first


def inv_groups():
    return [(ACCOUNT_NAME + '.shared', SHARED),
            (ACCOUNT_NAME + '.materials', MATERIALS),
            (ACCOUNT_NAME + '.bank', BANK)]


def char_invs():
    return list(CHARACTERS.items())


def rows(item_ids=(), dump_all=False, with_wallet=False, groups=None, chars=None):
    """build_rows with the filter wired the way main() wires it."""
    item_ids = list(item_ids)
    id_filter = set(item_ids) if (item_ids and not dump_all) else None
    return build_rows(
        ACCOUNT_NAME,
        inv_groups() if groups is None else groups,
        char_invs() if chars is None else chars,
        items_dict(), prices_dict(), item_ids,
        id_filter=id_filter, dump_all=dump_all,
        wallet=WALLET if with_wallet else None,
        currencies=list(CURRENCIES.values()) if with_wallet else None,
    )


class FilteringTest(unittest.TestCase):
    """One item asked for means one item returned, from every section alike."""

    def test_single_id_filters_every_section(self):
        out = rows([SHINY])
        self.assertEqual({r[ITEM_ID] for r in out}, {SHINY})
        self.assertEqual({r[ITEM_NAME] for r in out}, {SHINY_NAME})

    def test_sections_contribute_what_they_hold(self):
        out = rows([SHINY])
        by_section = {r[CHARACTER]: r[AMOUNT] for r in out}
        self.assertEqual(by_section[ACCOUNT_NAME + '.shared'], 1)
        self.assertEqual(by_section[ACCOUNT_NAME + '.bank'], 3)
        # Materials hold no baubles, so they produce no row at all.
        self.assertNotIn(ACCOUNT_NAME + '.materials', by_section)

    def test_several_ids(self):
        out = rows([SHINY, ECTO])
        self.assertEqual({r[ITEM_ID] for r in out}, {SHINY, ECTO})

    def test_id_nobody_owns_still_reports_per_character(self):
        # MINI is in no inventory. Storage contributes nothing; each character gets a
        # zero row, which is how mom sees "none of you have this".
        out = rows([MINI])
        self.assertEqual([r[CHARACTER] for r in out], list(CHARACTERS))
        self.assertEqual({r[AMOUNT] for r in out}, {0})

    def test_dump_all_ignores_the_filter(self):
        out = rows([SHINY], dump_all=True)
        self.assertIn(ECTO, {r[ITEM_ID] for r in out})
        self.assertIn(TRANSFORM, {r[ITEM_ID] for r in out})

    def test_no_ids_and_no_dump_all_leaves_characters_out(self):
        # Long-standing corner: storage is dumped whole, but the character loop has no
        # ids to walk, so it contributes nothing. Pinned to catch an accidental change.
        out = rows([])
        self.assertEqual([r[CHARACTER] for r in out if r[CHARACTER] in CHARACTERS], [])
        self.assertIn(ECTO, {r[ITEM_ID] for r in out})

    def test_failed_character_fetch_is_skipped(self):
        out = rows([SHINY], chars=[('Hoarder', CHARACTERS['Hoarder']), ('Brokechar', None)])
        self.assertEqual([r[CHARACTER] for r in out if r[CHARACTER] == 'Brokechar'], [])

    def test_every_row_has_one_cell_per_column(self):
        for row in rows([SHINY], with_wallet=True):
            self.assertEqual(len(row), len(extractor.COLUMNS))


class WalletTest(unittest.TestCase):
    """Currencies are a different namespace that shares the Item ID column."""

    def test_omitted_when_not_asked_for(self):
        self.assertEqual([r for r in rows([SHINY]) if r[CHARACTER].endswith('.wallet')], [])

    def test_included_when_asked_for(self):
        out = [r for r in rows(with_wallet=True) if r[CHARACTER].endswith('.wallet')]
        self.assertEqual(len(out), len(CURRENCIES))

    def test_currency_rows_carry_no_value(self):
        for r in rows(with_wallet=True):
            if r[CHARACTER].endswith('.wallet'):
                self.assertEqual(r[VALUE], '')
                self.assertEqual(r[SOURCE], extractor.NO_VALUE_SOURCE)

    def test_currency_amount_is_the_balance(self):
        out = {r[ITEM_ID]: r[AMOUNT] for r in rows(with_wallet=True)
               if r[CHARACTER].endswith('.wallet')}
        self.assertEqual(out[1], 123456)      # Coin
        self.assertEqual(out[4], 800)         # Gem, not the Assassin Transform Weapon
        self.assertEqual(out[61], 42)         # Research Note, not the Spineguard

    def test_currency_with_no_balance_reports_zero(self):
        out = build_rows(ACCOUNT_NAME, [], [], items_dict(), prices_dict(), [],
                         wallet=[], currencies=list(CURRENCIES.values()))
        self.assertEqual({r[AMOUNT] for r in out}, {0})

    def test_currency_names_win_over_colliding_item_names(self):
        # ids 4 and 61 exist in both namespaces. A wallet row must read as the currency.
        out = {r[ITEM_ID]: r[ITEM_NAME] for r in rows(with_wallet=True)
               if r[CHARACTER].endswith('.wallet')}
        self.assertEqual(out[4], 'Gem')
        self.assertEqual(out[61], 'Research Note')


class ValueRungTest(unittest.TestCase):
    """First rung that applies wins: TP if listable, else vendor, else nothing."""

    def test_tradable_and_unbound_uses_tp_net_of_fee(self):
        value, source = item_value(ECTO, False, items_dict(), prices_dict())
        self.assertEqual(source, 'TP')
        listed = prices_dict()[ECTO]['sells']['unit_price']
        self.assertEqual(value, format_coin(listed * extractor.TP_FEE_MULTIPLIER))

    def test_binding_demotes_to_vendor_rather_than_emptying(self):
        value, source = item_value(ECTO, True, items_dict(), prices_dict())
        self.assertEqual(source, 'Vendor')
        self.assertEqual(value, format_coin(items_dict()[ECTO]['vendor_value']))

    def test_untradable_with_vendor_value_uses_vendor(self):
        value, source = item_value(SHINY, False, items_dict(), prices_dict())
        self.assertEqual(source, 'Vendor')
        self.assertEqual(value, '0.3000')  # vendor_value 3000 - static game data

    def test_nosell_blocks_the_vendor_rung(self):
        # Mini Princess Miya advertises vendor_value 50 while carrying NoSell. Trusting
        # the number would print a price she cannot get.
        self.assertGreater(items_dict()[MINI]['vendor_value'], 0)
        self.assertIn('NoSell', items_dict()[MINI]['flags'])
        self.assertEqual(item_value(MINI, False, items_dict(), prices_dict()),
                         ('', extractor.NO_VALUE_SOURCE))

    def test_no_vendor_value_and_no_price_means_nothing(self):
        self.assertEqual(item_value(TRANSFORM, False, items_dict(), prices_dict()),
                         ('', extractor.NO_VALUE_SOURCE))

    def test_bound_tradable_nosell_falls_all_the_way_through(self):
        # Eternity is listable, so an unbound copy is worth a lot; a bound copy cannot
        # be listed and NoSell blocks the vendor, so it has no reachable value.
        self.assertEqual(item_value(ETERNITY, False, items_dict(), prices_dict())[1], 'TP')
        self.assertEqual(item_value(ETERNITY, True, items_dict(), prices_dict()),
                         ('', extractor.NO_VALUE_SOURCE))

    def test_unknown_id_does_not_crash(self):
        self.assertEqual(item_value(999999999, False, items_dict(), prices_dict()),
                         ('', extractor.NO_VALUE_SOURCE))


class BindingAggregationTest(unittest.TestCase):
    """A row covers every copy a character holds, so binding is a property of the set."""

    @staticmethod
    def char(entries):
        return [('Mule', {'bags': [{'inventory': entries}]})]

    def value_of(self, entries):
        out = rows([ECTO], chars=self.char(entries), groups=[])
        self.assertEqual(len(out), 1)
        return out[0][AMOUNT], out[0][SOURCE]

    def test_counts_are_summed_across_bags(self):
        out = rows([ECTO], groups=[], chars=[('Mule', {'bags': [
            {'inventory': [{'id': ECTO, 'count': 3, 'binding': None}]},
            {'inventory': [{'id': ECTO, 'count': 4, 'binding': None}]},
        ]})])
        self.assertEqual(out[0][AMOUNT], 7)

    def test_one_unbound_copy_keeps_the_tp_price_reachable(self):
        amount, source = self.value_of([{'id': ECTO, 'count': 1, 'binding': 'Account'},
                                        {'id': ECTO, 'count': 1, 'binding': None}])
        self.assertEqual(amount, 2)
        self.assertEqual(source, 'TP')

    def test_all_copies_bound_demotes_the_row(self):
        _, source = self.value_of([{'id': ECTO, 'count': 1, 'binding': 'Account'},
                                   {'id': ECTO, 'count': 1, 'binding': 'Character'}])
        self.assertEqual(source, 'Vendor')

    def test_zero_row_is_not_treated_as_bound(self):
        # Nothing held means nothing to bind; the row should still show what one is worth.
        amount, source = self.value_of([])
        self.assertEqual(amount, 0)
        self.assertEqual(source, 'TP')


class WalletFirstTest(unittest.TestCase):
    """Wallet totals belong at the top, grouped, however many accounts ran."""

    def test_wallet_rows_move_to_the_front(self):
        out = wallet_first([['a', 'a.bank', 1], ['a', 'a.wallet', 2], ['a', 'Char', 3]])
        self.assertEqual([r[1] for r in out], ['a.wallet', 'a.bank', 'Char'])

    def test_several_accounts_group_together(self):
        out = wallet_first([['a', 'a.wallet', 1], ['a', 'Char', 2],
                            ['b', 'b.wallet', 3], ['b', 'Char', 4]])
        self.assertEqual([r[1] for r in out], ['a.wallet', 'b.wallet', 'Char', 'Char'])

    def test_order_within_each_part_is_preserved(self):
        out = wallet_first([['a', 'a.bank', 1], ['a', 'a.shared', 2], ['a', 'a.materials', 3]])
        self.assertEqual([r[1] for r in out], ['a.bank', 'a.shared', 'a.materials'])

    def test_no_wallet_rows_changes_nothing(self):
        given = [['a', 'a.bank', 1], ['a', 'Char', 2]]
        self.assertEqual(wallet_first(given), given)


if __name__ == '__main__':
    unittest.main(verbosity=2)

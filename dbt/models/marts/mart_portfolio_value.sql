-- THE DELIVERABLE: one row per ticker per day (from that ticker's first trade onward),
-- with the position's value and unrealized gain/loss in USD and in Naira.
--
-- Notes
--  * shares_held and cost_basis are running totals of all trades up to that day.
--  * The Naira rate for a day is the latest published rate on or before that day,
--    so a day missing from the API reuses the previous day's rate.
--  * Naira gain/loss = USD gain/loss x that day's rate (valued at the day's exchange rate).
with prices as (
    select * from {{ ref('stg_stock_prices') }}
),

trades as (
    select * from {{ ref('stg_trades') }}
),

rates as (
    select * from {{ ref('stg_exchange_rates') }}
),

daily_rates as (
    select
        d.price_date,
        (
            select r.usd_to_ngn
            from rates r
            where r.rate_date <= d.price_date
            order by r.rate_date desc
            limit 1
        ) as usd_to_ngn
    from (select distinct price_date from prices) d
),

positions as (
    select
        p.price_date,
        p.ticker,
        p.close_price_usd,
        sum(t.shares)                    as shares_held,
        sum(t.shares * t.price_paid_usd) as cost_basis_usd
    from prices p
    inner join trades t
        on  t.ticker = p.ticker
        and t.trade_date <= p.price_date
    group by p.price_date, p.ticker, p.close_price_usd
)

select
    pos.ticker || '|' || pos.price_date::text                                   as position_key,
    pos.price_date,
    pos.ticker,
    pos.shares_held,
    round(pos.cost_basis_usd / pos.shares_held, 4)                              as avg_cost_usd,
    pos.close_price_usd,
    round(pos.cost_basis_usd, 2)                                                as cost_basis_usd,
    round(pos.shares_held * pos.close_price_usd, 2)                             as market_value_usd,
    round(pos.shares_held * pos.close_price_usd - pos.cost_basis_usd, 2)        as unrealized_gain_loss_usd,
    round((pos.shares_held * pos.close_price_usd - pos.cost_basis_usd)
          / pos.cost_basis_usd * 100, 2)                                        as unrealized_return_pct,
    r.usd_to_ngn,
    round(pos.shares_held * pos.close_price_usd * r.usd_to_ngn, 2)              as market_value_ngn,
    round((pos.shares_held * pos.close_price_usd - pos.cost_basis_usd)
          * r.usd_to_ngn, 2)                                                    as unrealized_gain_loss_ngn
from positions pos
left join daily_rates r
    on r.price_date = pos.price_date

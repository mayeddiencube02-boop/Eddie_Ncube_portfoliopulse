-- Whole-portfolio totals per day, in USD and Naira side by side.
select
    price_date,
    count(*)                            as positions_held,
    sum(cost_basis_usd)                 as total_cost_basis_usd,
    sum(market_value_usd)               as total_market_value_usd,
    sum(unrealized_gain_loss_usd)       as total_unrealized_gain_loss_usd,
    max(usd_to_ngn)                     as usd_to_ngn,
    sum(market_value_ngn)               as total_market_value_ngn,
    sum(unrealized_gain_loss_ngn)       as total_unrealized_gain_loss_ngn
from {{ ref('mart_portfolio_value') }}
group by price_date

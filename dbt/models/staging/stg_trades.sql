-- The Google Sheet arrives as text, so every column is cast to its real type.
-- Blank rows (common in sheets) are dropped.
select
    cast(trim(trade_id) as integer)         as trade_id,
    cast(trim("date") as date)              as trade_date,
    upper(trim(ticker))                     as ticker,
    cast(trim(shares) as numeric)           as shares,
    cast(trim(price_paid) as numeric(12,4)) as price_paid_usd
from {{ source('raw', 'trades') }}
where trade_id is not null
  and trim(trade_id) <> ''

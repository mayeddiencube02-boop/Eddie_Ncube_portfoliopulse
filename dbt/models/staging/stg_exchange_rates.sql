-- Each API record holds every currency in a JSON column called "usd".
-- We keep only the Naira rate: how many NGN one USD buys on that date.
select
    cast("date" as date)           as rate_date,
    cast(usd ->> 'ngn' as numeric) as usd_to_ngn
from {{ source('raw', 'api_usd_ngn_rates') }}
where usd ->> 'ngn' is not null

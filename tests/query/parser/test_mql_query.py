from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict

import pytest

from snuba.datasets.entities.entity_key import EntityKey
from snuba.datasets.entities.factory import get_entity
from snuba.datasets.factory import get_dataset
from snuba.query import OrderBy, OrderByDirection, SelectedExpression
from snuba.query.conditions import combine_and_conditions
from snuba.query.data_source.simple import Entity as QueryEntity
from snuba.query.dsl import (
    and_cond,
    arrayElement,
    column,
    equals,
    greaterOrEquals,
    in_fn,
    less,
    literal,
    literals_tuple,
    snuba_tags_raw,
)
from snuba.query.expressions import (
    Column,
    CurriedFunctionCall,
    FunctionCall,
    Literal,
    SubscriptableReference,
)
from snuba.query.logical import Query
from snuba.query.mql.parser import parse_mql_query
from snuba.query.parser.exceptions import ParsingException

# Commonly used expressions
from_distributions = from_clause = QueryEntity(
    EntityKey.GENERIC_METRICS_DISTRIBUTIONS,
    get_entity(EntityKey.GENERIC_METRICS_DISTRIBUTIONS).get_data_model(),
)

time_expression = FunctionCall(
    "_snuba_time",
    "toStartOfInterval",
    (
        Column("_snuba_timestamp", None, "timestamp"),
        FunctionCall(None, "toIntervalSecond", (Literal(None, 60),)),
        Literal(None, "Universal"),
    ),
)

mql_test_cases = [
    pytest.param(
        """sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]} by (transaction, status_code)""",
        {
            "start": "2023-11-23T18:30:00",
            "end": "2023-11-23T22:30:00",
            "rollup": {
                "granularity": 60,
                "interval": 60,
                "with_totals": "False",
                "orderby": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [11],
                "use_case_id": "transactions",
            },
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
                "transaction": 111111,
                "status_code": 222222,
            },
            "limit": None,
            "offset": None,
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                ),
                SelectedExpression("transaction", snuba_tags_raw(int(111111))),
                SelectedExpression("status_code", snuba_tags_raw(int(222222))),
                SelectedExpression(
                    "time",
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(60),)),
                            literal("Universal"),
                        ),
                    ),
                ),
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2023, 11, 23, 18, 30)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2023, 11, 23, 22, 30)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(11)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                in_fn(
                    snuba_tags_raw(int(888)),
                    literals_tuple(None, [literal("dist1"), literal("dist2")]),
                ),
            ),
            groupby=[
                snuba_tags_raw(int(111111)),
                snuba_tags_raw(int(222222)),
                FunctionCall(
                    "_snuba_time",
                    "toStartOfInterval",
                    (
                        column("timestamp", None, "_snuba_timestamp"),
                        FunctionCall(None, "toIntervalSecond", (literal(60),)),
                        literal("Universal"),
                    ),
                ),
            ],
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(60),)),
                            literal("Universal"),
                        ),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="test of resolved query",
    ),
    pytest.param(
        """sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}""",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": "ASC",
                "granularity": 60,
                "interval": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 0, 0)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 2, 0, 0)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                in_fn(
                    snuba_tags_raw(int(888)),
                    literals_tuple(None, [literal("dist1"), literal("dist2")]),
                ),
            ),
            groupby=None,
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="Select metric with filter",
    ),
    pytest.param(
        """sum(`d:transactions/duration@millisecond`){}""",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": "ASC",
                "granularity": 60,
                "interval": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {"d:transactions/duration@millisecond": 123456},
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 0, 0)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 2, 0, 0)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
            ),
            groupby=None,
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="Select metric with empty filter",
    ),
    pytest.param(
        """quantiles(0.5, 0.75)(s:transactions/user@none{!dist:["dist1", "dist2"]}){foo: bar} by (transaction)""",
        {
            "start": "2021-01-01T01:36:00",
            "end": "2021-01-05T04:15:00",
            "rollup": {
                "orderby": None,
                "granularity": 3600,
                "interval": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": 100,
            "offset": 3,
            "indexer_mappings": {
                "transaction.user": "s:transactions/user@none",
                "s:transactions/user@none": 567890,
                "dist": 888888,
                "foo": 777777,
                "transaction": 111111,
            },
        },
        Query(
            from_clause=QueryEntity(
                EntityKey.GENERIC_METRICS_SETS,
                get_entity(EntityKey.GENERIC_METRICS_SETS).get_data_model(),
            ),
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    CurriedFunctionCall(
                        "_snuba_aggregate_value",
                        FunctionCall(None, "quantiles", (literal(0.5), literal(0.75))),
                        (column("value", None, "_snuba_value"),),
                    ),
                ),
                SelectedExpression("transaction", snuba_tags_raw(int(111111))),
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 1, 36)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 5, 4, 15)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(
                    column("granularity", None, "_snuba_granularity"), literal(3600)
                ),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(567890)),
                FunctionCall(
                    None,
                    "notIn",
                    (
                        snuba_tags_raw(int(888888)),
                        literals_tuple(None, [literal("dist1"), literal("dist2")]),
                    ),
                ),
                equals(snuba_tags_raw(int(777777)), literal("bar")),
            ),
            groupby=[snuba_tags_raw(int(111111))],
            having=None,
            order_by=None,
            limitby=None,
            limit=100,
            offset=3,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="Select metric with filter and groupby",
    ),
    pytest.param(
        """quantiles(0.5)(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]} by (transaction, status_code)""",
        {
            "start": "2023-11-23T18:30:00",
            "end": "2023-11-23T22:30:00",
            "rollup": {
                "granularity": 60,
                "interval": 60,
                "with_totals": "False",
                "orderby": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [11],
                "use_case_id": "transactions",
            },
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
                "transaction": 111111,
                "status_code": 222222,
            },
            "limit": None,
            "offset": None,
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    arrayElement(
                        "_snuba_aggregate_value",
                        CurriedFunctionCall(
                            None,
                            FunctionCall(None, "quantiles", (literal(0.5),)),
                            (column("value", None, "_snuba_value"),),
                        ),
                        literal(1),
                    ),
                ),
                SelectedExpression("transaction", snuba_tags_raw(int(111111))),
                SelectedExpression("status_code", snuba_tags_raw(int(222222))),
                SelectedExpression(
                    "time",
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(60),)),
                            literal("Universal"),
                        ),
                    ),
                ),
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2023, 11, 23, 18, 30)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2023, 11, 23, 22, 30)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(11)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                in_fn(
                    snuba_tags_raw(int(888)),
                    literals_tuple(None, [literal("dist1"), literal("dist2")]),
                ),
            ),
            groupby=[
                snuba_tags_raw(int(111111)),
                snuba_tags_raw(int(222222)),
                FunctionCall(
                    "_snuba_time",
                    "toStartOfInterval",
                    (
                        column("timestamp", None, "_snuba_timestamp"),
                        FunctionCall(None, "toIntervalSecond", (literal(60),)),
                        literal("Universal"),
                    ),
                ),
            ],
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(60),)),
                            literal("Universal"),
                        ),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="curried function",
    ),
    pytest.param(
        """sum(`d:sessions/duration@second`){release:["foo", "bar"]} by release""",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": "ASC",
                "granularity": 60,
                "interval": None,
                "with_totals": None,
            },
            "scope": {"org_ids": [1], "project_ids": [1], "use_case_id": "sessions"},
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:sessions/duration@second": 123456,
                "release": 111,
                "foo": 222,
                "bar": 333,
            },
        },
        Query(
            from_clause=QueryEntity(
                EntityKey.METRICS_DISTRIBUTIONS,
                get_entity(EntityKey.METRICS_DISTRIBUTIONS).get_data_model(),
            ),
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                ),
                SelectedExpression(
                    "release",
                    SubscriptableReference(
                        "_snuba_tags[111]",
                        column("tags", None, "_snuba_tags"),
                        literal("111"),
                    ),
                ),
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 0, 0)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 2, 0, 0)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("sessions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                in_fn(
                    SubscriptableReference(
                        "_snuba_tags[111]",
                        column("tags", None, "_snuba_tags"),
                        literal("111"),
                    ),
                    literals_tuple(None, [literal(222), literal(333)]),
                ),
            ),
            groupby=[
                SubscriptableReference(
                    "_snuba_tags[111]",
                    column("tags", None, "_snuba_tags"),
                    literal("111"),
                )
            ],
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "sum",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "metrics",
        id="Select metric with filter for metrics dataset",
    ),
    pytest.param(
        """max(d:transactions/duration@millisecond){bar:" !\\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"} by (transaction)""",
        {
            "start": "2024-01-07T13:35:00+00:00",
            "end": "2024-01-08T13:40:00+00:00",
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~": 78910,
                "bar": 111213,
                "transaction": 141516,
            },
            "limit": 10000,
            "offset": None,
            "rollup": {
                "granularity": 60,
                "interval": 300,
                "orderby": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "max",
                        (column("value", None, "_snuba_value"),),
                    ),
                ),
                SelectedExpression("transaction", snuba_tags_raw(int(141516))),
                SelectedExpression(
                    "time",
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(300),)),
                            literal("Universal"),
                        ),
                    ),
                ),
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2024, 1, 7, 13, 35)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2024, 1, 8, 13, 40)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                equals(
                    snuba_tags_raw(int(111213)),
                    literal(
                        " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
                    ),
                ),
            ),
            groupby=[
                snuba_tags_raw(int(141516)),
                FunctionCall(
                    "_snuba_time",
                    "toStartOfInterval",
                    (
                        column("timestamp", None, "_snuba_timestamp"),
                        FunctionCall(None, "toIntervalSecond", (literal(300),)),
                        literal("Universal"),
                    ),
                ),
            ],
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_time",
                        "toStartOfInterval",
                        (
                            column("timestamp", None, "_snuba_timestamp"),
                            FunctionCall(None, "toIntervalSecond", (literal(300),)),
                            literal("Universal"),
                        ),
                    ),
                )
            ],
            limitby=None,
            limit=10000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="test crazy characters",
    ),
    pytest.param(
        """apdex(sum(`d:transactions/duration@millisecond`), 500){dist:["dist1", "dist2"]}""",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": "ASC",
                "granularity": 60,
                "interval": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "apdex",
                        (
                            FunctionCall(
                                None, "sum", (column("value", None, "_snuba_value"),)
                            ),
                            literal(500),
                        ),
                    ),
                )
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 0, 0)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 2, 0, 0)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
                in_fn(
                    snuba_tags_raw(int(888)),
                    literals_tuple(None, [literal("dist1"), literal("dist2")]),
                ),
            ),
            groupby=None,
            having=None,
            order_by=[
                OrderBy(
                    OrderByDirection.ASC,
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "apdex",
                        (
                            FunctionCall(
                                None, "sum", (column("value", None, "_snuba_value"),)
                            ),
                            literal(500),
                        ),
                    ),
                )
            ],
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="Select metric with arbitrary function",
    ),
    pytest.param(
        """topK(10)(sum(s:transactions/user@none), 300)""",
        {
            "start": "2021-01-01T01:36:00",
            "end": "2021-01-05T04:15:00",
            "rollup": {
                "orderby": None,
                "granularity": 3600,
                "interval": None,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": 100,
            "offset": 3,
            "indexer_mappings": {
                "transaction.user": "s:transactions/user@none",
                "s:transactions/user@none": 567890,
                "dist": 888888,
                "foo": 777777,
                "transaction": 111111,
            },
        },
        Query(
            from_clause=QueryEntity(
                EntityKey.GENERIC_METRICS_SETS,
                get_entity(EntityKey.GENERIC_METRICS_SETS).get_data_model(),
            ),
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    CurriedFunctionCall(
                        None,
                        FunctionCall(None, "topK", (literal(10),)),
                        (
                            FunctionCall(
                                "_snuba_aggregate_value",
                                "sum",
                                (column("value", None, "_snuba_value"),),
                            ),
                            literal(300),
                        ),
                    ),
                )
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 1, 36)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 5, 4, 15)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"),
                    literal("transactions"),
                ),
                equals(
                    column("granularity", None, "_snuba_granularity"), literal(3600)
                ),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(567890)),
            ),
            groupby=None,
            having=None,
            order_by=None,
            limitby=None,
            limit=100,
            offset=3,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="Select metric with curried arbitrary function",
    ),
    pytest.param(
        """avg(d:custom/sentry.event_manager.save_transactions.fetch_organizations@second){(event_type:"transaction" AND transaction:"sentry.tasks.store.save_event_transaction")}""",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": None,
                "with_totals": None,
            },
            "scope": {"org_ids": [1], "project_ids": [1], "use_case_id": "custom"},
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:custom/sentry.event_manager.save_transactions.fetch_organizations@second": 111111,
                "event_type": 222222,
                "transaction": 333333,
            },
        },
        Query(
            from_clause=from_clause,
            selected_columns=[
                SelectedExpression(
                    "aggregate_value",
                    FunctionCall(
                        "_snuba_aggregate_value",
                        "avg",
                        (column("value", None, "_snuba_value"),),
                    ),
                )
            ],
            array_join=None,
            condition=and_cond(
                greaterOrEquals(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 1, 0, 0)),
                ),
                less(
                    column("timestamp", None, "_snuba_timestamp"),
                    literal(datetime(2021, 1, 2, 0, 0)),
                ),
                in_fn(
                    column("project_id", None, "_snuba_project_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                in_fn(
                    column("org_id", None, "_snuba_org_id"),
                    literals_tuple(None, [literal(1)]),
                ),
                equals(
                    column("use_case_id", None, "_snuba_use_case_id"), literal("custom")
                ),
                equals(column("granularity", None, "_snuba_granularity"), literal(60)),
                equals(column("metric_id", None, "_snuba_metric_id"), literal(111111)),
                equals(snuba_tags_raw(int(222222)), literal("transaction")),
                equals(
                    snuba_tags_raw(int(333333)),
                    literal("sentry.tasks.store.save_event_transaction"),
                ),
            ),
            groupby=None,
            having=None,
            order_by=None,
            limitby=None,
            limit=1000,
            offset=0,
            totals=False,
            granularity=None,
        ),
        "generic_metrics",
        id="complex condition case",
    ),
    # pytest.param(
    #     'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]} by (transaction, status_code)',
    #     {
    #         "start": "2023-11-23T18:30:00",
    #         "end": "2023-11-23T22:30:00",
    #         "rollup": {
    #             "granularity": 60,
    #             "interval": 60,
    #             "with_totals": "False",
    #             "orderby": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [11],
    #             "use_case_id": "transactions",
    #         },
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #             "dist": 888,
    #             "transaction": 111111,
    #             "status_code": 222222,
    #         },
    #         "limit": None,
    #         "offset": None,
    #     },
    #     Query(
    #         from_distributions,
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "sum",
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "transaction",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[111111]",
    #                     Column("_snuba_tags_raw", None, "tags_raw"),
    #                     Literal(None, "111111"),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "status_code",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[222222]",
    #                     Column("_snuba_tags_raw", None, "tags_raw"),
    #                     Literal(None, "222222"),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "time",
    #                 time_expression,
    #             ),
    #         ],
    #         groupby=[
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[111111]",
    #                 Column("_snuba_tags_raw", None, "tags_raw"),
    #                 Literal(None, "111111"),
    #             ),
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[222222]",
    #                 Column("_snuba_tags_raw", None, "tags_raw"),
    #                 Literal(None, "222222"),
    #             ),
    #             time_expression,
    #         ],
    #         condition=and_cond(
    #             greaterOrEquals(
    #                 column("timestamp", None, "_snuba_timestamp"),
    #                 literal(datetime(2023, 11, 23, 18, 30)),
    #             ),
    #             less(
    #                 column("timestamp", None, "_snuba_timestamp"),
    #                 literal(datetime(2023, 11, 23, 22, 30)),
    #             ),
    #             in_fn(
    #                 column("project_id", None, "_snuba_project_id"),
    #                 literals_tuple(None, [literal(11)]),
    #             ),
    #             in_fn(
    #                 column("org_id", None, "_snuba_org_id"),
    #                 literals_tuple(None, [literal(1)]),
    #             ),
    #             equals(
    #                 column("use_case_id", None, "_snuba_use_case_id"),
    #                 literal("transactions"),
    #             ),
    #             equals(column("granularity", None, "_snuba_granularity"), literal(60)),
    #             equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
    #             in_fn(
    #                 snuba_tags_raw(int(888)),
    #                 literals_tuple(None, [literal("dist1"), literal("dist2")]),
    #             ),
    #         ),
    #         order_by=[
    #             OrderBy(
    #                 direction=OrderByDirection.ASC,
    #                 expression=time_expression,
    #             )
    #         ],
    #         limit=1000,
    #         offset=0,
    #     ),
    #     "generic_metrics",
    #     id="test of resolved query",
    # ),
    # pytest.param(
    #     'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}',
    #     {
    #         "start": "2021-01-01T00:00:00",
    #         "end": "2021-01-02T00:00:00",
    #         "rollup": {
    #             "orderby": "ASC",
    #             "granularity": 60,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #         "limit": None,
    #         "offset": None,
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #             "dist": 888,
    #         },
    #     },
    #     Query(
    #         from_clause=from_clause,
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "sum",
    #                     (column("value", None, "_snuba_value"),),
    #                 ),
    #             )
    #         ],
    #         array_join=None,
    #         condition=and_cond(
    #             greaterOrEquals(
    #                 column("timestamp", None, "_snuba_timestamp"),
    #                 literal(datetime(2021, 1, 1, 0, 0)),
    #             ),
    #             less(
    #                 column("timestamp", None, "_snuba_timestamp"),
    #                 literal(datetime(2021, 1, 2, 0, 0)),
    #             ),
    #             in_fn(
    #                 column("project_id", None, "_snuba_project_id"),
    #                 literals_tuple(None, [literal(1)]),
    #             ),
    #             in_fn(
    #                 column("org_id", None, "_snuba_org_id"),
    #                 literals_tuple(None, [literal(1)]),
    #             ),
    #             equals(
    #                 column("use_case_id", None, "_snuba_use_case_id"),
    #                 literal("transactions"),
    #             ),
    #             equals(column("granularity", None, "_snuba_granularity"), literal(60)),
    #             equals(column("metric_id", None, "_snuba_metric_id"), literal(123456)),
    #             in_fn(
    #                 snuba_tags_raw(int(888)),
    #                 literals_tuple(None, [literal("dist1"), literal("dist2")]),
    #             ),
    #         ),
    #         groupby=None,
    #         having=None,
    #         order_by=[
    #             OrderBy(
    #                 OrderByDirection.ASC,
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "sum",
    #                     (column("value", None, "_snuba_value"),),
    #                 ),
    #             )
    #         ],
    #         limitby=None,
    #         limit=1000,
    #         offset=0,
    #         totals=False,
    #         granularity=None,
    #     ),
    #     "generic_metrics",
    #     id="Select metric with filter",
    # ),
    # pytest.param(
    #     "sum(`d:transactions/duration@millisecond`){}",
    #     {
    #         "start": "2021-01-01T00:00:00",
    #         "end": "2021-01-02T00:00:00",
    #         "rollup": {
    #             "orderby": "ASC",
    #             "granularity": 60,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #         "limit": None,
    #         "offset": None,
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_DISTRIBUTIONS,
    #             get_entity(EntityKey.GENERIC_METRICS_DISTRIBUTIONS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "sum",
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #         ],
    #         groupby=[],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column(
    #                                     "_snuba_project_id",
    #                                     None,
    #                                     "project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "transactions"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2021, 1, 1, 0, 0
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2021,
    #                                                                         1,
    #                                                                         2,
    #                                                                         0,
    #                                                                         0,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "equals",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_metric_id",
    #                                                                     None,
    #                                                                     "metric_id",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     123456,
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         order_by=[
    #             OrderBy(
    #                 OrderByDirection.ASC,
    #                 FunctionCall(
    #                     alias="_snuba_aggregate_value",
    #                     function_name="sum",
    #                     parameters=(
    #                         (
    #                             Column(
    #                                 alias="_snuba_value",
    #                                 table_name=None,
    #                                 column_name="value",
    #                             ),
    #                         )
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         limit=1000,
    #     ),
    #     "generic_metrics",
    #     id="Select metric with empty filter",
    # ),
    # pytest.param(
    #     'quantiles(0.5, 0.75)(s:transactions/user@none{!dist:["dist1", "dist2"]}){foo: bar} by (transaction)',
    #     {
    #         "start": "2021-01-01T01:36:00",
    #         "end": "2021-01-05T04:15:00",
    #         "rollup": {
    #             "orderby": None,
    #             "granularity": 3600,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #         "limit": 100,
    #         "offset": 3,
    #         "indexer_mappings": {
    #             "transaction.user": "s:transactions/user@none",
    #             "s:transactions/user@none": 567890,
    #             "dist": 888888,
    #             "foo": 777777,
    #             "transaction": 111111,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_SETS,
    #             get_entity(EntityKey.GENERIC_METRICS_SETS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 CurriedFunctionCall(
    #                     "_snuba_aggregate_value",
    #                     FunctionCall(
    #                         None, "quantiles", (Literal(None, 0.5), Literal(None, 0.75))
    #                     ),
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "transaction",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[111111]",
    #                     Column(
    #                         "_snuba_tags_raw",
    #                         None,
    #                         "tags_raw",
    #                     ),
    #                     Literal(None, "111111"),
    #                 ),
    #             ),
    #         ],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 3600),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column("_snuba_project_id", None, "project_id"),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "transactions"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2021, 1, 1, 1, 36
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2021,
    #                                                                         1,
    #                                                                         5,
    #                                                                         4,
    #                                                                         15,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "and",
    #                                                             (
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "equals",
    #                                                                     (
    #                                                                         Column(
    #                                                                             "_snuba_metric_id",
    #                                                                             None,
    #                                                                             "metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             None,
    #                                                                             567890,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "and",
    #                                                                     (
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "notIn",
    #                                                                             (
    #                                                                                 SubscriptableReference(
    #                                                                                     "_snuba_tags_raw[888888]",
    #                                                                                     column=Column(
    #                                                                                         "_snuba_tags_raw",
    #                                                                                         None,
    #                                                                                         "tags_raw",
    #                                                                                     ),
    #                                                                                     key=Literal(
    #                                                                                         None,
    #                                                                                         "888888",
    #                                                                                     ),
    #                                                                                 ),
    #                                                                                 FunctionCall(
    #                                                                                     None,
    #                                                                                     "tuple",
    #                                                                                     (
    #                                                                                         Literal(
    #                                                                                             None,
    #                                                                                             "dist1",
    #                                                                                         ),
    #                                                                                         Literal(
    #                                                                                             None,
    #                                                                                             "dist2",
    #                                                                                         ),
    #                                                                                     ),
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "equals",
    #                                                                             (
    #                                                                                 SubscriptableReference(
    #                                                                                     "_snuba_tags_raw[777777]",
    #                                                                                     column=Column(
    #                                                                                         "_snuba_tags_raw",
    #                                                                                         None,
    #                                                                                         "tags_raw",
    #                                                                                     ),
    #                                                                                     key=Literal(
    #                                                                                         None,
    #                                                                                         "777777",
    #                                                                                     ),
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "bar",
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         order_by=[],
    #         groupby=[
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[111111]",
    #                 Column(
    #                     "_snuba_tags_raw",
    #                     None,
    #                     "tags_raw",
    #                 ),
    #                 Literal(None, "111111"),
    #             )
    #         ],
    #         limit=100,
    #         offset=3,
    #     ),
    #     "generic_metrics",
    #     id="Select metric with filter and groupby",
    # ),
    # pytest.param(
    #     'quantiles(0.5)(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]} by (transaction, status_code)',
    #     {
    #         "start": "2023-11-23T18:30:00",
    #         "end": "2023-11-23T22:30:00",
    #         "rollup": {
    #             "granularity": 60,
    #             "interval": 60,
    #             "with_totals": "False",
    #             "orderby": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [11],
    #             "use_case_id": "transactions",
    #         },
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #             "dist": 888,
    #             "transaction": 111111,
    #             "status_code": 222222,
    #         },
    #         "limit": None,
    #         "offset": None,
    #     },
    #     Query(
    #         from_distributions,
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 arrayElement(
    #                     "_snuba_aggregate_value",
    #                     CurriedFunctionCall(
    #                         None,
    #                         FunctionCall(
    #                             None,
    #                             "quantiles",
    #                             (Literal(None, 0.5),),
    #                         ),
    #                         (Column("_snuba_value", None, "value"),),
    #                     ),
    #                     Literal(None, 1),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "transaction",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[111111]",
    #                     Column("_snuba_tags_raw", None, "tags_raw"),
    #                     Literal(None, "111111"),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "status_code",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[222222]",
    #                     Column("_snuba_tags_raw", None, "tags_raw"),
    #                     Literal(None, "222222"),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "time",
    #                 time_expression,
    #             ),
    #         ],
    #         groupby=[
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[111111]",
    #                 Column("_snuba_tags_raw", None, "tags_raw"),
    #                 Literal(None, "111111"),
    #             ),
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[222222]",
    #                 Column("_snuba_tags_raw", None, "tags_raw"),
    #                 Literal(None, "222222"),
    #             ),
    #             time_expression,
    #         ],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column(
    #                                     "_snuba_project_id",
    #                                     None,
    #                                     "project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 11),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "transactions"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2023, 11, 23, 18, 30
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2023,
    #                                                                         11,
    #                                                                         23,
    #                                                                         22,
    #                                                                         30,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "and",
    #                                                             (
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "equals",
    #                                                                     (
    #                                                                         Column(
    #                                                                             "_snuba_metric_id",
    #                                                                             None,
    #                                                                             "metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             None,
    #                                                                             123456,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "in",
    #                                                                     (
    #                                                                         SubscriptableReference(
    #                                                                             "_snuba_tags_raw[888]",
    #                                                                             column=Column(
    #                                                                                 "_snuba_tags_raw",
    #                                                                                 None,
    #                                                                                 "tags_raw",
    #                                                                             ),
    #                                                                             key=Literal(
    #                                                                                 None,
    #                                                                                 "888",
    #                                                                             ),
    #                                                                         ),
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "tuple",
    #                                                                             (
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "dist1",
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "dist2",
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         order_by=[
    #             OrderBy(
    #                 direction=OrderByDirection.ASC,
    #                 expression=time_expression,
    #             )
    #         ],
    #         limit=1000,
    #         offset=0,
    #     ),
    #     "generic_metrics",
    #     id="curried function",
    # ),
    # pytest.param(
    #     'sum(`d:sessions/duration@second`){release:["foo", "bar"]} by release',
    #     {
    #         "start": "2021-01-01T00:00:00",
    #         "end": "2021-01-02T00:00:00",
    #         "rollup": {
    #             "orderby": "ASC",
    #             "granularity": 60,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "sessions",
    #         },
    #         "limit": None,
    #         "offset": None,
    #         "indexer_mappings": {
    #             "d:sessions/duration@second": 123456,
    #             "release": 111,
    #             "foo": 222,
    #             "bar": 333,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.METRICS_DISTRIBUTIONS,
    #             get_entity(EntityKey.METRICS_DISTRIBUTIONS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "sum",
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "release",
    #                 SubscriptableReference(
    #                     "_snuba_tags[111]",
    #                     Column(
    #                         "_snuba_tags",
    #                         None,
    #                         "tags",
    #                     ),
    #                     Literal(None, "111"),
    #                 ),
    #             ),
    #         ],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column(
    #                                     "_snuba_project_id",
    #                                     None,
    #                                     "project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "sessions"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2021, 1, 1, 0, 0
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2021,
    #                                                                         1,
    #                                                                         2,
    #                                                                         0,
    #                                                                         0,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "and",
    #                                                             (
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "equals",
    #                                                                     (
    #                                                                         Column(
    #                                                                             "_snuba_metric_id",
    #                                                                             None,
    #                                                                             "metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             None,
    #                                                                             123456,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "in",
    #                                                                     (
    #                                                                         SubscriptableReference(
    #                                                                             "_snuba_tags[111]",
    #                                                                             column=Column(
    #                                                                                 "_snuba_tags",
    #                                                                                 None,
    #                                                                                 "tags",
    #                                                                             ),
    #                                                                             key=Literal(
    #                                                                                 None,
    #                                                                                 "111",
    #                                                                             ),
    #                                                                         ),
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "tuple",
    #                                                                             (
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     222,
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     333,
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         groupby=[
    #             SubscriptableReference(
    #                 "_snuba_tags[111]",
    #                 Column(
    #                     "_snuba_tags",
    #                     None,
    #                     "tags",
    #                 ),
    #                 Literal(None, "111"),
    #             )
    #         ],
    #         order_by=[
    #             OrderBy(
    #                 OrderByDirection.ASC,
    #                 FunctionCall(
    #                     alias="_snuba_aggregate_value",
    #                     function_name="sum",
    #                     parameters=(
    #                         (
    #                             Column(
    #                                 alias="_snuba_value",
    #                                 table_name=None,
    #                                 column_name="value",
    #                             ),
    #                         )
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         limit=1000,
    #     ),
    #     "metrics",
    #     id="Select metric with filter for metrics dataset",
    # ),
    # pytest.param(
    #     'max(d:transactions/duration@millisecond){bar:" !\\"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"} by (transaction)',
    #     {
    #         "start": "2024-01-07T13:35:00+00:00",
    #         "end": "2024-01-08T13:40:00+00:00",
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #             " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~": 78910,
    #             "bar": 111213,
    #             "transaction": 141516,
    #         },
    #         "limit": 10000,
    #         "offset": None,
    #         "rollup": {
    #             "granularity": 60,
    #             "interval": 300,
    #             "orderby": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_DISTRIBUTIONS,
    #             get_entity(EntityKey.GENERIC_METRICS_DISTRIBUTIONS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "max",
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "transaction",
    #                 SubscriptableReference(
    #                     "_snuba_tags_raw[141516]",
    #                     Column("_snuba_tags_raw", None, "tags_raw"),
    #                     Literal(None, "141516"),
    #                 ),
    #             ),
    #             SelectedExpression(
    #                 "time",
    #                 FunctionCall(
    #                     "_snuba_time",
    #                     "toStartOfInterval",
    #                     (
    #                         Column("_snuba_timestamp", None, "timestamp"),
    #                         FunctionCall(
    #                             None, "toIntervalSecond", (Literal(None, 300),)
    #                         ),
    #                         Literal(None, "Universal"),
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         condition=FunctionCall(
    #             alias=None,
    #             function_name="and",
    #             parameters=(
    #                 FunctionCall(
    #                     alias=None,
    #                     function_name="equals",
    #                     parameters=(
    #                         Column(
    #                             alias="_snuba_granularity",
    #                             table_name=None,
    #                             column_name="granularity",
    #                         ),
    #                         Literal(alias=None, value=60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     alias=None,
    #                     function_name="and",
    #                     parameters=(
    #                         FunctionCall(
    #                             alias=None,
    #                             function_name="in",
    #                             parameters=(
    #                                 Column(
    #                                     alias="_snuba_project_id",
    #                                     table_name=None,
    #                                     column_name="project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     alias=None,
    #                                     function_name="tuple",
    #                                     parameters=(Literal(alias=None, value=1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             alias=None,
    #                             function_name="and",
    #                             parameters=(
    #                                 FunctionCall(
    #                                     alias=None,
    #                                     function_name="in",
    #                                     parameters=(
    #                                         Column(
    #                                             alias="_snuba_org_id",
    #                                             table_name=None,
    #                                             column_name="org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             alias=None,
    #                                             function_name="tuple",
    #                                             parameters=(
    #                                                 Literal(alias=None, value=1),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     alias=None,
    #                                     function_name="and",
    #                                     parameters=(
    #                                         FunctionCall(
    #                                             alias=None,
    #                                             function_name="equals",
    #                                             parameters=(
    #                                                 Column(
    #                                                     alias="_snuba_use_case_id",
    #                                                     table_name=None,
    #                                                     column_name="use_case_id",
    #                                                 ),
    #                                                 Literal(
    #                                                     alias=None, value="transactions"
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             alias=None,
    #                                             function_name="and",
    #                                             parameters=(
    #                                                 FunctionCall(
    #                                                     alias=None,
    #                                                     function_name="greaterOrEquals",
    #                                                     parameters=(
    #                                                         Column(
    #                                                             alias="_snuba_timestamp",
    #                                                             table_name=None,
    #                                                             column_name="timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             alias=None,
    #                                                             value=datetime(
    #                                                                 2024, 1, 7, 13, 35
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     alias=None,
    #                                                     function_name="and",
    #                                                     parameters=(
    #                                                         FunctionCall(
    #                                                             alias=None,
    #                                                             function_name="less",
    #                                                             parameters=(
    #                                                                 Column(
    #                                                                     alias="_snuba_timestamp",
    #                                                                     table_name=None,
    #                                                                     column_name="timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     alias=None,
    #                                                                     value=datetime(
    #                                                                         2024,
    #                                                                         1,
    #                                                                         8,
    #                                                                         13,
    #                                                                         40,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             alias=None,
    #                                                             function_name="and",
    #                                                             parameters=(
    #                                                                 FunctionCall(
    #                                                                     alias=None,
    #                                                                     function_name="equals",
    #                                                                     parameters=(
    #                                                                         Column(
    #                                                                             alias="_snuba_metric_id",
    #                                                                             table_name=None,
    #                                                                             column_name="metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             alias=None,
    #                                                                             value=123456,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     alias=None,
    #                                                                     function_name="equals",
    #                                                                     parameters=(
    #                                                                         SubscriptableReference(
    #                                                                             alias="_snuba_tags_raw[111213]",
    #                                                                             column=Column(
    #                                                                                 alias="_snuba_tags_raw",
    #                                                                                 table_name=None,
    #                                                                                 column_name="tags_raw",
    #                                                                             ),
    #                                                                             key=Literal(
    #                                                                                 alias=None,
    #                                                                                 value="111213",
    #                                                                             ),
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             alias=None,
    #                                                                             value=" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         groupby=[
    #             SubscriptableReference(
    #                 "_snuba_tags_raw[141516]",
    #                 Column(
    #                     "_snuba_tags_raw",
    #                     None,
    #                     "tags_raw",
    #                 ),
    #                 Literal(None, "141516"),
    #             ),
    #             FunctionCall(
    #                 alias="_snuba_time",
    #                 function_name="toStartOfInterval",
    #                 parameters=(
    #                     Column(
    #                         alias="_snuba_timestamp",
    #                         table_name=None,
    #                         column_name="timestamp",
    #                     ),
    #                     FunctionCall(
    #                         alias=None,
    #                         function_name="toIntervalSecond",
    #                         parameters=(Literal(alias=None, value=300),),
    #                     ),
    #                     Literal(alias=None, value="Universal"),
    #                 ),
    #             ),
    #         ],
    #         order_by=[
    #             OrderBy(
    #                 direction=OrderByDirection.ASC,
    #                 expression=FunctionCall(
    #                     alias="_snuba_time",
    #                     function_name="toStartOfInterval",
    #                     parameters=(
    #                         Column(
    #                             alias="_snuba_timestamp",
    #                             table_name=None,
    #                             column_name="timestamp",
    #                         ),
    #                         FunctionCall(
    #                             alias=None,
    #                             function_name="toIntervalSecond",
    #                             parameters=(Literal(alias=None, value=300),),
    #                         ),
    #                         Literal(alias=None, value="Universal"),
    #                     ),
    #                 ),
    #             )
    #         ],
    #         limit=10000,
    #     ),
    #     "generic_metrics",
    #     id="test crazy characters",
    # ),
    # pytest.param(
    #     'apdex(sum(`d:transactions/duration@millisecond`), 500){dist:["dist1", "dist2"]}',
    #     {
    #         "start": "2021-01-01T00:00:00",
    #         "end": "2021-01-02T00:00:00",
    #         "rollup": {
    #             "orderby": "ASC",
    #             "granularity": 60,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #         "limit": None,
    #         "offset": None,
    #         "indexer_mappings": {
    #             "d:transactions/duration@millisecond": 123456,
    #             "dist": 888,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_DISTRIBUTIONS,
    #             get_entity(EntityKey.GENERIC_METRICS_DISTRIBUTIONS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "apdex",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "sum",
    #                             (Column("_snuba_value", None, "value"),),
    #                         ),
    #                         Literal(None, 500),
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         groupby=[],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column(
    #                                     "_snuba_project_id",
    #                                     None,
    #                                     "project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "transactions"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2021, 1, 1, 0, 0
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2021,
    #                                                                         1,
    #                                                                         2,
    #                                                                         0,
    #                                                                         0,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "and",
    #                                                             (
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "equals",
    #                                                                     (
    #                                                                         Column(
    #                                                                             "_snuba_metric_id",
    #                                                                             None,
    #                                                                             "metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             None,
    #                                                                             123456,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "in",
    #                                                                     (
    #                                                                         SubscriptableReference(
    #                                                                             "_snuba_tags_raw[888]",
    #                                                                             column=Column(
    #                                                                                 "_snuba_tags_raw",
    #                                                                                 None,
    #                                                                                 "tags_raw",
    #                                                                             ),
    #                                                                             key=Literal(
    #                                                                                 None,
    #                                                                                 "888",
    #                                                                             ),
    #                                                                         ),
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "tuple",
    #                                                                             (
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "dist1",
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "dist2",
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         order_by=[
    #             OrderBy(
    #                 OrderByDirection.ASC,
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "apdex",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "sum",
    #                             (Column("_snuba_value", None, "value"),),
    #                         ),
    #                         Literal(None, 500),
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         limit=1000,
    #     ),
    #     "generic_metrics",
    #     id="Select metric with arbitrary function",
    # ),
    # pytest.param(
    #     "topK(10)(sum(s:transactions/user@none), 300)",
    #     {
    #         "start": "2021-01-01T01:36:00",
    #         "end": "2021-01-05T04:15:00",
    #         "rollup": {
    #             "orderby": None,
    #             "granularity": 3600,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "transactions",
    #         },
    #         "limit": 100,
    #         "offset": 3,
    #         "indexer_mappings": {
    #             "transaction.user": "s:transactions/user@none",
    #             "s:transactions/user@none": 567890,
    #             "dist": 888888,
    #             "foo": 777777,
    #             "transaction": 111111,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_SETS,
    #             get_entity(EntityKey.GENERIC_METRICS_SETS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 CurriedFunctionCall(
    #                     None,
    #                     FunctionCall(None, "topK", (Literal(None, 10),)),
    #                     (
    #                         FunctionCall(
    #                             "_snuba_aggregate_value",
    #                             "sum",
    #                             (Column("_snuba_value", None, "value"),),
    #                         ),
    #                         Literal(None, 300),
    #                     ),
    #                 ),
    #             ),
    #         ],
    #         condition=and_cond(
    #             FunctionCall(
    #                 None,
    #                 "equals",
    #                 (column("granularity", "_snuba_granularity"), literal(3600)),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "in",
    #                 (
    #                     column("project_id", "_snuba_project_id"),
    #                     FunctionCall(None, "tuple", (literal(1),)),
    #                 ),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "in",
    #                 (
    #                     column("org_id", "_snuba_org_id"),
    #                     FunctionCall(None, "tuple", (literal(1),)),
    #                 ),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "equals",
    #                 (
    #                     column("use_case_id", "_snuba_use_case_id"),
    #                     literal("transactions"),
    #                 ),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "greaterOrEquals",
    #                 (
    #                     column("timestamp", "_snuba_timestamp"),
    #                     literal(datetime(2021, 1, 1, 1, 36)),
    #                 ),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "less",
    #                 (
    #                     column("timestamp", "_snuba_timestamp"),
    #                     literal(datetime(2021, 1, 5, 4, 15)),
    #                 ),
    #             ),
    #             FunctionCall(
    #                 None,
    #                 "equals",
    #                 (column("metric_id", "_snuba_metric_id"), literal(567890)),
    #             ),
    #         ),
    #         # condition=and_cond(
    #         #     FunctionCall(
    #         #         None,
    #         #         "equals",
    #         #         (column("granularity", "_snuba_granularity"), literal(3600)),
    #         #     ),
    #         #     FunctionCall(
    #         #         None,
    #         #         "in",
    #         #         (
    #         #             column("project_id", "_snuba_project_id"),
    #         #             FunctionCall(None, "tuple", (literal(1),)),
    #         #         ),
    #         #     ),
    #         # ),
    #         # condition=FunctionCall(
    #         #     None,
    #         #     "and",
    #         #     (
    #         #         FunctionCall(
    #         #             None,
    #         #             "equals",
    #         #             (
    #         #                 Column(
    #         #                     "_snuba_granularity",
    #         #                     None,
    #         #                     "granularity",
    #         #                 ),
    #         #                 Literal(None, 3600),
    #         #             ),
    #         #         ),
    #         #         FunctionCall(
    #         #             None,
    #         #             "and",
    #         #             (
    #         #                 FunctionCall(
    #         #                     None,
    #         #                     "in",
    #         #                     (
    #         #                         Column("_snuba_project_id", None, "project_id"),
    #         #                         FunctionCall(
    #         #                             None,
    #         #                             "tuple",
    #         #                             (Literal(None, 1),),
    #         #                         ),
    #         #                     ),
    #         #                 ),
    #         #                 FunctionCall(
    #         #                     None,
    #         #                     "and",
    #         #                     (
    #         #                         FunctionCall(
    #         #                             None,
    #         #                             "in",
    #         #                             (
    #         #                                 Column(
    #         #                                     "_snuba_org_id",
    #         #                                     None,
    #         #                                     "org_id",
    #         #                                 ),
    #         #                                 FunctionCall(
    #         #                                     None,
    #         #                                     "tuple",
    #         #                                     (Literal(None, 1),),
    #         #                                 ),
    #         #                             ),
    #         #                         ),
    #         #                         FunctionCall(
    #         #                             None,
    #         #                             "and",
    #         #                             (
    #         #                                 FunctionCall(
    #         #                                     None,
    #         #                                     "equals",
    #         #                                     (
    #         #                                         Column(
    #         #                                             "_snuba_use_case_id",
    #         #                                             None,
    #         #                                             "use_case_id",
    #         #                                         ),
    #         #                                         Literal(None, "transactions"),
    #         #                                     ),
    #         #                                 ),
    #         #                                 FunctionCall(
    #         #                                     None,
    #         #                                     "and",
    #         #                                     (
    #         #                                         FunctionCall(
    #         #                                             None,
    #         #                                             "greaterOrEquals",
    #         #                                             (
    #         #                                                 Column(
    #         #                                                     "_snuba_timestamp",
    #         #                                                     None,
    #         #                                                     "timestamp",
    #         #                                                 ),
    #         #                                                 Literal(
    #         #                                                     None,
    #         #                                                     datetime(
    #         #                                                         2021, 1, 1, 1, 36
    #         #                                                     ),
    #         #                                                 ),
    #         #                                             ),
    #         #                                         ),
    #         #                                         FunctionCall(
    #         #                                             None,
    #         #                                             "and",
    #         #                                             (
    #         #                                                 FunctionCall(
    #         #                                                     None,
    #         #                                                     "less",
    #         #                                                     (
    #         #                                                         Column(
    #         #                                                             "_snuba_timestamp",
    #         #                                                             None,
    #         #                                                             "timestamp",
    #         #                                                         ),
    #         #                                                         Literal(
    #         #                                                             None,
    #         #                                                             datetime(
    #         #                                                                 2021,
    #         #                                                                 1,
    #         #                                                                 5,
    #         #                                                                 4,
    #         #                                                                 15,
    #         #                                                             ),
    #         #                                                         ),
    #         #                                                     ),
    #         #                                                 ),
    #         #                                                 FunctionCall(
    #         #                                                     None,
    #         #                                                     "equals",
    #         #                                                     (
    #         #                                                         Column(
    #         #                                                             "_snuba_metric_id",
    #         #                                                             None,
    #         #                                                             "metric_id",
    #         #                                                         ),
    #         #                                                         Literal(
    #         #                                                             None,
    #         #                                                             567890,
    #         #                                                         ),
    #         #                                                     ),
    #         #                                                 ),
    #         #                                             ),
    #         #                                         ),
    #         #                                     ),
    #         #                                 ),
    #         #                             ),
    #         #                         ),
    #         #                     ),
    #         #                 ),
    #         #             ),
    #         #         ),
    #         #     ),
    #         # ),
    #         order_by=[],
    #         limit=100,
    #         offset=3,
    #     ),
    #     "generic_metrics",
    #     id="Select metric with curried arbitrary function",
    # ),
    # pytest.param(
    #     'avg(d:custom/sentry.event_manager.save_transactions.fetch_organizations@second){(event_type:"transaction" AND transaction:"sentry.tasks.store.save_event_transaction")}',
    #     {
    #         "start": "2021-01-01T00:00:00",
    #         "end": "2021-01-02T00:00:00",
    #         "rollup": {
    #             "orderby": None,
    #             "granularity": 60,
    #             "interval": None,
    #             "with_totals": None,
    #         },
    #         "scope": {
    #             "org_ids": [1],
    #             "project_ids": [1],
    #             "use_case_id": "custom",
    #         },
    #         "limit": None,
    #         "offset": None,
    #         "indexer_mappings": {
    #             "d:custom/sentry.event_manager.save_transactions.fetch_organizations@second": 111111,
    #             "event_type": 222222,
    #             "transaction": 333333,
    #         },
    #     },
    #     Query(
    #         QueryEntity(
    #             EntityKey.GENERIC_METRICS_DISTRIBUTIONS,
    #             get_entity(EntityKey.GENERIC_METRICS_DISTRIBUTIONS).get_data_model(),
    #         ),
    #         selected_columns=[
    #             SelectedExpression(
    #                 "aggregate_value",
    #                 FunctionCall(
    #                     "_snuba_aggregate_value",
    #                     "avg",
    #                     (Column("_snuba_value", None, "value"),),
    #                 ),
    #             ),
    #         ],
    #         condition=FunctionCall(
    #             None,
    #             "and",
    #             (
    #                 FunctionCall(
    #                     None,
    #                     "equals",
    #                     (
    #                         Column(
    #                             "_snuba_granularity",
    #                             None,
    #                             "granularity",
    #                         ),
    #                         Literal(None, 60),
    #                     ),
    #                 ),
    #                 FunctionCall(
    #                     None,
    #                     "and",
    #                     (
    #                         FunctionCall(
    #                             None,
    #                             "in",
    #                             (
    #                                 Column(
    #                                     "_snuba_project_id",
    #                                     None,
    #                                     "project_id",
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "tuple",
    #                                     (Literal(None, 1),),
    #                                 ),
    #                             ),
    #                         ),
    #                         FunctionCall(
    #                             None,
    #                             "and",
    #                             (
    #                                 FunctionCall(
    #                                     None,
    #                                     "in",
    #                                     (
    #                                         Column(
    #                                             "_snuba_org_id",
    #                                             None,
    #                                             "org_id",
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "tuple",
    #                                             (Literal(None, 1),),
    #                                         ),
    #                                     ),
    #                                 ),
    #                                 FunctionCall(
    #                                     None,
    #                                     "and",
    #                                     (
    #                                         FunctionCall(
    #                                             None,
    #                                             "equals",
    #                                             (
    #                                                 Column(
    #                                                     "_snuba_use_case_id",
    #                                                     None,
    #                                                     "use_case_id",
    #                                                 ),
    #                                                 Literal(None, "custom"),
    #                                             ),
    #                                         ),
    #                                         FunctionCall(
    #                                             None,
    #                                             "and",
    #                                             (
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "greaterOrEquals",
    #                                                     (
    #                                                         Column(
    #                                                             "_snuba_timestamp",
    #                                                             None,
    #                                                             "timestamp",
    #                                                         ),
    #                                                         Literal(
    #                                                             None,
    #                                                             datetime(
    #                                                                 2021, 1, 1, 0, 0
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                                 FunctionCall(
    #                                                     None,
    #                                                     "and",
    #                                                     (
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "less",
    #                                                             (
    #                                                                 Column(
    #                                                                     "_snuba_timestamp",
    #                                                                     None,
    #                                                                     "timestamp",
    #                                                                 ),
    #                                                                 Literal(
    #                                                                     None,
    #                                                                     datetime(
    #                                                                         2021,
    #                                                                         1,
    #                                                                         2,
    #                                                                         0,
    #                                                                         0,
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                         FunctionCall(
    #                                                             None,
    #                                                             "and",
    #                                                             (
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "equals",
    #                                                                     (
    #                                                                         Column(
    #                                                                             "_snuba_metric_id",
    #                                                                             None,
    #                                                                             "metric_id",
    #                                                                         ),
    #                                                                         Literal(
    #                                                                             None,
    #                                                                             111111,
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                                 FunctionCall(
    #                                                                     None,
    #                                                                     "and",
    #                                                                     (
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "equals",
    #                                                                             (
    #                                                                                 SubscriptableReference(
    #                                                                                     "_snuba_tags_raw[222222]",
    #                                                                                     column=Column(
    #                                                                                         "_snuba_tags_raw",
    #                                                                                         None,
    #                                                                                         "tags_raw",
    #                                                                                     ),
    #                                                                                     key=Literal(
    #                                                                                         None,
    #                                                                                         "222222",
    #                                                                                     ),
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "transaction",
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                         FunctionCall(
    #                                                                             None,
    #                                                                             "equals",
    #                                                                             (
    #                                                                                 SubscriptableReference(
    #                                                                                     "_snuba_tags_raw[333333]",
    #                                                                                     column=Column(
    #                                                                                         "_snuba_tags_raw",
    #                                                                                         None,
    #                                                                                         "tags_raw",
    #                                                                                     ),
    #                                                                                     key=Literal(
    #                                                                                         None,
    #                                                                                         "333333",
    #                                                                                     ),
    #                                                                                 ),
    #                                                                                 Literal(
    #                                                                                     None,
    #                                                                                     "sentry.tasks.store.save_event_transaction",
    #                                                                                 ),
    #                                                                             ),
    #                                                                         ),
    #                                                                     ),
    #                                                                 ),
    #                                                             ),
    #                                                         ),
    #                                                     ),
    #                                                 ),
    #                                             ),
    #                                         ),
    #                                     ),
    #                                 ),
    #                             ),
    #                         ),
    #                     ),
    #                 ),
    #             ),
    #         ),
    #         groupby=[],
    #         order_by=[],
    #         limit=1000,
    #     ),
    #     "generic_metrics",
    # ),
]


def reprall():
    from snuba.query.dsl_mapper import query_repr

    for testc in mql_test_cases:
        print("pytest.param(")
        print(f'    """{testc[0][0]}""",')
        print(f"    {repr(testc[0][1])},")
        print(f"    {query_repr(testc[0][2])},")
        print(f"    {repr(testc[0][3])},")
        print(f"    id={repr(testc.id)},")
        print("),")


@pytest.mark.parametrize(
    "query_body, mql_context, expected_query, dataset", mql_test_cases
)
def test_format_expressions_from_mql(
    query_body: str, mql_context: Dict[str, Any], expected_query: Query, dataset: str
) -> None:
    generic_metrics = get_dataset(dataset)
    query, _ = parse_mql_query(str(query_body), mql_context, generic_metrics)
    eq, reason = query.equals(expected_query)
    assert eq, reason


invalid_mql_test_cases = [
    pytest.param(
        'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}',
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": 10,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("interval 10 must be greater than or equal to granularity 6"),
        id="interval less than granularity",
    ),
    pytest.param(
        'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}',
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": "DESC",
                "granularity": 60,
                "interval": 60,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("orderby is not supported when interval is specified"),
        id="interval and orderby provided",
    ),
    pytest.param(
        'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}',
        {
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": 60,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": None,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("MQL context: missing required field 'start'"),
        id="missing start time",
    ),
    pytest.param(
        'sum(`d:transactions/duration@millisecond`){dist:["dist1", "dist2"]}',
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": 60,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": 1000000,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("queries cannot have a limit higher than 10000"),
        id="missing limit",
    ),
    pytest.param(
        'sum(`transaction.duration`){dist:["dist1", "dist2"]}',
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": 60,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": 1000000,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("MQL endpoint only supports MRIs"),
        id="only mris",
    ),
    pytest.param(
        "sum(`transaction.duration",
        {
            "start": "2021-01-01T00:00:00",
            "end": "2021-01-02T00:00:00",
            "rollup": {
                "orderby": None,
                "granularity": 60,
                "interval": 60,
                "with_totals": None,
            },
            "scope": {
                "org_ids": [1],
                "project_ids": [1],
                "use_case_id": "transactions",
            },
            "limit": 1000000,
            "offset": None,
            "indexer_mappings": {
                "d:transactions/duration@millisecond": 123456,
                "dist": 888,
            },
        },
        ParsingException("Parsing error on line 1 at 'um(`transacti'"),
        id="incomplete error test",
    ),
]


@pytest.mark.parametrize("query_body, mql_context, error", invalid_mql_test_cases)
def test_invalid_format_expressions_from_mql(
    query_body: str,
    mql_context: Dict[str, Any],
    error: Exception,
) -> None:
    generic_metrics = get_dataset("generic_metrics")
    with pytest.raises(type(error), match=re.escape(str(error))):
        query, _ = parse_mql_query(query_body, mql_context, generic_metrics)


def test_pushdown_error_query() -> None:
    mql = '((avg(d:transactions/duration@millisecond) * 100.0) * 100.0){transaction:"getsentry.tasks.calculate_spike_projections"}'
    context = {
        "end": "2024-04-08T06:49:00+00:00",
        "indexer_mappings": {
            "d:transactions/duration@millisecond": 9223372036854775909,
            "transaction": 9223372036854776020,
        },
        "limit": 10000,
        "offset": None,
        "rollup": {
            "granularity": 60,
            "interval": 60,
            "orderby": None,
            "with_totals": None,
        },
        "scope": {
            "org_ids": [1],
            "project_ids": [1],
            "use_case_id": "'transactions'",
        },
        "start": "2024-04-08T05:48:00+00:00",
    }
    parse_mql_query(mql, context, get_dataset("generic_metrics"))

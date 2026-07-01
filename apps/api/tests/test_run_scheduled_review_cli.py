from app.cli.run_scheduled_review import parse_args


def test_parse_args_accepts_template_and_lookback_days() -> None:
    args = parse_args(
        [
            "--template",
            "bad_actor_watchlist",
            "--lookback-days",
            "30",
        ]
    )

    assert args.template == "bad_actor_watchlist"
    assert args.lookback_days == 30

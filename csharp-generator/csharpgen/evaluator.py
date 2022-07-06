from silvera.evaluation.registration import EvaluationDesc


def arch_eval(model, output_dir, output_format):
    print(model)
    print(output_dir)
    print(output_format)


myeval = EvaluationDesc(
    name="custom",
    description="My custom architecture evaluator.",
    eval_func=arch_eval
)

from tensorflow.keras.metrics import Metric, Recall, Precision
from tensorflow.python.ops import math_ops


class F1Score(Metric):
    """Computes the F1 score"""

    def __init__(self, name="f1-score", dtype=None):
        super().__init__(name=name, dtype=dtype)
        self.precision_metric = Precision()
        self.recall_metric = Recall()

    def update_state(self, y_true, y_pred, sample_weight=None):
        self.precision_metric.update_state(y_true, y_pred, sample_weight)
        self.recall_metric.update_state(y_true, y_pred, sample_weight)

    def result(self):
        recall_inverse = math_ops.div_no_nan(1.0, self.recall_metric.result())
        precision_inverse = math_ops.div_no_nan(1.0, self.precision_metric.result())
        return math_ops.div_no_nan(2.0, recall_inverse + precision_inverse)

    def reset_state(self):
        self.precision_metric.reset_state()
        self.recall_metric.reset_state()

    def get_config(self):
        return dict(
            precision=self.precision_metric.get_config(),
            recall=self.precision_metric.get_config(),
        )

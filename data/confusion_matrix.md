# Confusion Matrix — Predicted vs. Actual Bug Categories

Evaluated on the 98-bug held-out test set (20% of 490).

|                          | Algorithmic Inefficiency | Memory Usage | Redundant Computation | CPU Overhead | I/O Inefficiency |
|--------------------------|--------------------------|--------------|-----------------------|--------------|------------------|
| **Algorithmic Inefficiency** | 30 | 1 | 1 | 1 | 0 |
| **Memory Usage**             |  2 | 19 | 0 | 2 | 0 |
| **Redundant Computation**    |  0 | 1 |  9 | 1 | 0 |
| **CPU Overhead**             |  2 | 1 |  1 | 16 | 0 |
| **I/O Inefficiency**         |  1 | 0 |  1 | 1 | 8 |

Rows = actual category, columns = predicted category. Diagonal entries are correct
predictions.

## Key Observations

- **Strongest category:** Algorithmic Inefficiency — 30/33 correct (90.9%).
- **Most common confusion:** Algorithmic Inefficiency ↔ CPU Overhead. Inefficient
  algorithms often increase CPU usage, blurring the boundary.
- **Memory Usage** misclassifications go to Algorithmic Inefficiency or CPU Overhead
  (object creation in loops resembles algorithmic / CPU-heavy patterns).
- **I/O Inefficiency** has the most spread-out errors, consistent with its lower
  detection rate (72.7%) and longer files (avg. 290 lines).

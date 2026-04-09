# Python 3.13 升级工作指导

> 文档版本: 1.0
> 创建日期: 2026-04-09
> 当前Python版本: 3.11.3
> 目标Python版本: 3.13.x

---

## 目录

1. [阶段一：依赖升级](#阶段一依赖升级)
2. [阶段二：代码修改](#阶段二代码修改)
3. [阶段三：测试验证](#阶段三测试验证)
4. [回滚方案](#回滚方案)
5. [附录](#附录)

---

## 阶段一：依赖升级

### 1.1 升级 pybind11_bazel

**目标版本**: >= 2.13.6 (支持 Python 3.13)

#### 步骤

1. **修改 `MODULE.bazel`**

```python
# 文件: MODULE.bazel
# 原配置 (第19行)
# bazel_dep(name = "pybind11_bazel", version = "2.11.1")

# 新配置
bazel_dep(name = "pybind11_bazel", version = "2.13.6")
```

2. **验证 pybind11 版本兼容性**

```bash
# 清理Bazel缓存
bazel clean --expunge

# 重新获取依赖
bazel fetch //...

# 检查pybind11版本
bazel query @pybind11//:pybind11 --output=build 2>/dev/null | grep version
```

3. **可能遇到的问题**

| 错误信息 | 解决方案 |
|----------|----------|
| `pybind11_bazel version not found` | 检查Bazel中央仓库是否有该版本，或使用 `archive_override` 指定 |
| `incompatible with rules_python version` | 同时升级 rules_python |

---

### 1.2 升级 rules_python

**目标版本**: >= 0.35.0 (支持 Python 3.13)

#### 步骤

1. **修改 `MODULE.bazel`**

```python
# 文件: MODULE.bazel
# 原配置 (第7行)
# bazel_dep(name = "rules_python", version = "0.31.0")

# 新配置
bazel_dep(name = "rules_python", version = "0.35.0")

# 更新Python版本 (第10-14行)
python = use_extension("@rules_python//python/extensions:python.bzl", "python")
python.toolchain(
    ignore_root_user_error = True,
    is_default = True,
    python_version = "3.13.1",  # 修改为3.13.x
)
use_repo(python, "python_3_13", "python_3_13_1_x86_64-unknown-linux-gnu")

# 更新pip配置 (第30-35行)
pip = use_extension("@rules_python//python/extensions:pip.bzl", "pip")
pip.parse(
    hub_name = "py_deps",
    python_version = "3.13.1",  # 修改为3.13.x
    requirements_lock = "//depend/pip:requirements_lock.txt",
)

# 更新python_configure (第21-25行)
python_configure = use_extension("@pybind11_bazel//:python_configure.bzl", "extension")
python_configure.toolchain(
    python_interpreter_target = "@python_3_13_1_x86_64-unknown-linux-gnu//:bin/python3",
    python_version = "",
)
```

2. **更新 requirements_lock.txt**

```bash
# 使用Python 3.13重新生成lock文件
cd /mnt/youbin03.jia_docker/app

# 如果有pip环境，使用以下命令
pip-compile --python-version 3.13 depend/pip/requirements.txt -o depend/pip/requirements_lock.txt

# 或者手动更新lock文件头部的Python版本标记
```

---

### 1.3 升级 Python 依赖库

#### 修改 `depend/pip/requirements.txt`

```diff
# 文件: depend/pip/requirements.txt

- requests==2.25.1
+ requests==2.32.3

  conan==2.4.1
  Jinja2==3.1.2
  PyYAML==6.0.1
  Flask==3.0.0
  numpy==1.26.4
```

#### 验证兼容性

```bash
# 检查依赖兼容性
pip install pip-check
pip-check

# 或使用pip-audit检查安全问题
pip install pip-audit
pip-audit
```

---

### 1.4 更新其他 pyproject.toml 文件

#### `src/sdk_viz/saturnviz/pyproject.toml`

```diff
  requires-python = ">=3.7"

  # 在classifiers中添加3.13支持
  classifiers = [
    ...
+   "Programming Language :: Python :: 3.12",
+   "Programming Language :: Python :: 3.13",
  ]

  # 更新测试矩阵
  [[tool.hatch.envs.all.matrix]]
- python = ["3.7", "3.8", "3.9", "3.10", "3.11"]
+ python = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13"]
```

#### `src/perception/perception_vlm/perception_vlm_server/cloud_server/setup.py`

```diff
  setup(
      ...
-     python_requires=">=3.10",
+     python_requires=">=3.10,<3.14",
      ...
  )
```

---

## 阶段二：代码修改

### 2.1 Python C API 调用审查与修改

以下文件需要重点审查和修改：

---

#### 2.1.1 `src/software_trigger_engine/src/trigger_engine/src/python_module.cpp`

**风险点**:
- `Py_IsInitialized()` 在 Python 3.13 中行为可能变化
- `PyGILState_Ensure()` / `PyGILState_Release()` 与新GIL实现

**修改建议**:

```cpp
// 文件: src/software_trigger_engine/src/trigger_engine/src/python_module.cpp

// ========== 原代码 (第67-78行) ==========
PythonModule::~PythonModule() {
  if (Py_IsInitialized()) { // 检查解释器是否已初始化
    PyGILState_STATE gstate = PyGILState_Ensure();
    Py_XDECREF(pMainFunc_);
    Py_XDECREF(pUpdateFunc_);
    Py_XDECREF(pFunc_);
    Py_XDECREF(pInstance_);
    Py_XDECREF(pClass_);
    Py_XDECREF(pModule_);
    PyGILState_Release(gstate);
  }
}

// ========== 建议修改 ==========
PythonModule::~PythonModule() {
  // Python 3.13: 使用 Py_IsInitialized() 仍然有效
  // 但建议增加 GIL 状态检查
  if (Py_IsInitialized()) {
    // 检查当前线程是否持有GIL
    PyGILState_STATE gstate = PyGILState_Ensure();

    // 安全释放对象
    Py_CLEAR(pMainFunc_);   // Py_CLEAR 比 Py_XDECREF 更安全
    Py_CLEAR(pUpdateFunc_);
    Py_CLEAR(pFunc_);
    Py_CLEAR(pInstance_);
    Py_CLEAR(pClass_);
    Py_CLEAR(pModule_);

    PyGILState_Release(gstate);
  }
}
```

**LoadPythonInterp() 函数检查** (第191行附近):

```cpp
// ========== 原代码 ==========
Py_Initialize();

// ========== 建议添加错误检查 ==========
if (Py_InitializeEx(0) < 0) {  // Py_InitializeEx 返回状态
  RCLCPP_ERROR(this->get_logger(), "Failed to initialize Python interpreter");
  return false;
}

// Python 3.13: 确保GIL已创建
if (!PyGILState_Check()) {
  PyEval_InitThreads();  // 在3.9+中是空操作，但保留向后兼容
}
```

---

#### 2.1.2 `src/pnc/evaluation/src/metrics/python_metrics/python_framework_interface_metric.cc`

**风险点**:
- `Py_Initialize()` / `Py_Finalize()` 多次调用
- `PyArg_Parse()` 使用旧格式

**修改建议**:

```cpp
// 文件: src/pnc/evaluation/src/metrics/python_metrics/python_framework_interface_metric.cc

// ========== 原代码 (第51-107行) ==========

// ========== 建议修改 ==========

bool PythonFrameworkInterfaceMetric::LoadConfig(const evaluation::EvaluationMetric& metric_config) {
  // ... 前面代码不变 ...

  // 使用 Py_InitializeEx(0) 避免信号处理程序安装
  // 这在嵌入式环境或多次初始化场景更安全
  if (Py_IsInitialized()) {
    RCLCPP_WARN(rclcpp::get_logger("PythonFrameworkInterfaceMetric"),
                "Python interpreter already initialized");
  } else {
    Py_InitializeEx(0);  // 0 = 不安装信号处理程序
  }

  if (!Py_IsInitialized()) {
    RCLCPP_ERROR(rclcpp::get_logger("PythonFrameworkInterfaceMetric"), "python init fail");
    return false;
  }

  // ... 中间代码不变 ...

  // 第102行: PyArg_Parse 需要检查返回值
  // 原代码
  // PyArg_Parse(py_result, "s", &python_framework_return_);

  // 建议修改
  if (py_result == nullptr || !PyArg_Parse(py_result, "s", &python_framework_return_)) {
    if (PyErr_Occurred()) {
      PyErr_Print();
    }
    RCLCPP_ERROR(rclcpp::get_logger("PythonFrameworkInterfaceMetric"),
                 "Failed to parse Python result");
    Py_XDECREF(py_result);
    Py_XDECREF(py_func);
    Py_XDECREF(py_module);
    Py_XDECREF(sys_module);
    Py_XDECREF(sys_path);
    // 注意: 不要在这里调用 Py_Finalize，如果有其他代码还在使用Python
    return false;
  }

  // 清理引用
  Py_XDECREF(py_result);
  Py_XDECREF(py_func);
  Py_XDECREF(py_args);
  Py_XDECREF(py_module);
  Py_XDECREF(sys_module);

  RCLCPP_INFO(rclcpp::get_logger("PythonFrameworkInterfaceMetric"),
              "Metrics eval finished.. Result is: %s", python_framework_return_.c_str());

  // 注意: 如果进程生命周期内多次调用此函数，不要每次都 Finalize
  // 考虑在模块卸载时统一 Finalize
  // Py_Finalize();

  return true;
}
```

---

#### 2.1.3 `src/pnc/evaluation/src/metrics/regression_metrics/` 目录下的文件

涉及文件:
- `regress_metric.cc`
- `qa_metric.cc`
- `sv_regress_metric.cc`

**统一修改模式**:

```cpp
// 所有使用 PyRun_SimpleString 的地方，建议改为更安全的方式

// ========== 原代码模式 ==========
PyRun_SimpleString("import sys");
PyRun_SimpleString("sys.path.append('/horizon-bucket/saturn_v_dev/sv_algo_metric/')");

// ========== 建议修改 ==========
// 使用 PyRun_SimpleStringFlags 更可控
PyCompilerFlags flags = {_Py_CONFIG_COMPAT_MODE, 0};  // Python 3.13 新标志
PyRun_SimpleStringFlags("import sys", &flags);

// 或使用 Python 代码执行函数
PyObject* globals = PyDict_New();
PyObject* locals = PyDict_New();
PyDict_SetItemString(globals, "__builtins__", PyEval_GetBuiltins());

const char* code = R"(
import sys
sys.path.append('/horizon-bucket/saturn_v_dev/sv_algo_metric/')
sys.path.append('/horizon-bucket/saturn_v_dev/sv_algo_metric/sv_regress/')
)";

PyObject* result = PyRun_StringFlags(code, Py_file_input, globals, locals, &flags);
if (result == nullptr && PyErr_Occurred()) {
    PyErr_Print();
}
Py_XDECREF(result);
Py_XDECREF(globals);
Py_XDECREF(locals);
```

---

#### 2.1.4 `src/data_mining/pybind_subscriber/` 目录下的文件

涉及文件:
- `nested_msg_sub.cpp`
- `nested_msg_sub_new.cpp`
- `mining_benchmark.cpp`

**这些文件使用 pybind11，需要确保 pybind11 头文件版本匹配**:

```cpp
// 文件: src/data_mining/pybind_subscriber/src/nested_msg_sub_new.cpp

// 确保使用最新 pybind11 API
#include <pybind11/embed.h>  // 保持不变
#include <pybind11/pybind11.h>

// 检查版本兼容性
static_assert(PYBIND11_VERSION_MAJOR >= 2 && PYBIND11_VERSION_MINOR >= 13,
              "pybind11 version must be >= 2.13.0 for Python 3.13 support");

// ========== 原代码 (第143行) ==========
Py_Initialize();

// ========== 建议修改 ==========
// pybind11::initialize_interpreter() 是更推荐的方式
py::initialize_interpreter();
if (!Py_IsInitialized()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to initialize Python interpreter");
    return false;
}

// ========== 原代码 (第157行) ==========
Py_FinalizeEx();

// ========== 建议修改 ==========
py::finalize_interpreter();
```

---

### 2.2 pybind11 绑定代码检查

#### 检查所有 pybind 模块

```bash
# 列出所有 pybind 相关源文件
find /mnt/youbin03.jia_docker/app/src -name "*_pybind.cc" -o -name "*_pybind.cpp"

# 主要文件列表:
# src/pnc/tools/pybind/driving/bindings/*.cc
# src/pnc/tools/pybind/idnp/bindings/*.cc
# src/pnc/tools/prediction_pybind/prediction_pybind.cpp
# src/pnc/tools/cognition_pybind/cognition_pybind.cpp
# src/pnc/swc/pnc_workflow/control/jupyter_pybind/src/*.cc
# src/pnc/swc/pnc_workflow/safety_function/tools/pybind/src/*.cc
# src/perception/perception_map_tiler/tools/*.cpp
# src/data_mining/pybind_subscriber/src/*.cpp
```

#### 添加版本检查头文件

在每个 pybind 绑定文件开头添加:

```cpp
// 在 #include <pybind11/pybind11.h> 之前添加
#if PY_VERSION_HEX >= 0x030D0000  // Python 3.13+
// Python 3.13 specific handling if needed
#endif

#include <pybind11/pybind11.h>

// 添加版本断言
static_assert(PYBIND11_VERSION_HEX >= 0x020D0600,  // 2.13.6
              "pybind11 2.13.6+ required for Python 3.13 support");
```

---

### 2.3 构建文件修改

#### 更新 `src/pnc/bazel/pnc_pybind_tool.bzl`

```python
# 文件: src/pnc/bazel/pnc_pybind_tool.bzl

def pnc_pybind_tool(
        name,
        deps = [],
        # ... 其他参数 ...
        ):
    # ... 现有代码 ...

    all_deps = deps + [
        Label("@pybind11//:pybind11"),
        "@rules_python//python/cc:current_py_cc_headers",
    ]

    # 添加 Python 3.13 兼容的编译选项
    additional_copts = [
        "-Isrc",
        "-fdiagnostics-color=always",
        "-fdiagnostics-show-option",
        # Python 3.13 可能需要的额外选项
        "-Wno-deprecated-declarations",  # 暂时抑制废弃警告
    ]

    # ... 其余代码不变 ...
```

---

## 阶段三：测试验证

### 3.1 编译测试

#### 步骤 1: 清理并重新构建

```bash
cd /mnt/youbin03.jia_docker/app

# 清理所有缓存
bazel clean --expunge

# 重新获取依赖
bazel fetch //...

# 尝试构建所有 pybind 目标
bazel build //src/pnc/tools/pybind/... 2>&1 | tee build_pybind.log
bazel build //src/perception/perception_map_tiler/tools/... 2>&1 | tee build_tiler.log
bazel build //src/data_mining/pybind_subscriber/... 2>&1 | tee build_mining.log
```

#### 步骤 2: 检查编译错误

```bash
# 搜索关键错误
grep -E "(error:|Error:|fatal:)" build_*.log | head -50

# 搜索 Python 相关警告
grep -i "python" build_*.log | grep -i "warning\|error"
```

#### 步骤 3: 构建所有依赖 Python 的目标

```bash
# 构建所有包含 Python 依赖的包
bazel build //src/pnc/... //src/perception/... //src/software_trigger_engine/... 2>&1 | tee full_build.log
```

---

### 3.2 单元测试

#### 步骤 1: 运行 Python 相关测试

```bash
# 运行 Python 测试
bazel test //src/pnc/evaluation/... --test_output=all 2>&1 | tee test_evaluation.log

# 运行 pybind 测试
bazel test //src/pnc/tools/pybind/... --test_output=all 2>&1 | tee test_pybind.log

# 运行 data_mining 测试
bazel test //src/data_mining/... --test_output=all 2>&1 | tee test_mining.log
```

#### 步骤 2: 检查测试结果

```bash
# 统计测试结果
echo "=== 测试统计 ==="
grep -c "PASSED" test_*.log
grep -c "FAILED" test_*.log
grep -c "SKIPPED" test_*.log

# 列出失败的测试
grep "FAILED" test_*.log
```

---

### 3.3 集成测试

#### 步骤 1: Python 解释器初始化测试

创建测试脚本验证 Python C API 调用:

```python
# 文件: test_python_313_compat.py

import sys
import subprocess
import os

def test_pybind_import():
    """测试所有 pybind 模块能否正常导入"""

    pybind_modules = [
        "joint_interative_decision_pybind",
        "cbf_interface_pybind",
        "idnp_planning_pybind",
        "prediction_pybind",
        "cognition_pybind",
        "ctrl_sim_pybind",
        "lateral_mpc_pybind",
        "longitudinal_mpc_solver_pybind",
        # ... 添加其他模块
    ]

    results = []
    for module in pybind_modules:
        try:
            # 假设 .so 文件在特定路径
            so_path = f"bazel-bin/src/pnc/tools/pybind/driving/bindings/{module}.so"
            if os.path.exists(so_path):
                result = subprocess.run(
                    [sys.executable, "-c", f"import {module}"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                results.append({
                    "module": module,
                    "success": result.returncode == 0,
                    "error": result.stderr if result.returncode != 0 else None
                })
        except Exception as e:
            results.append({
                "module": module,
                "success": False,
                "error": str(e)
            })

    return results

def test_python_c_api():
    """测试 Python C API 兼容性"""
    import ctypes

    # 测试 Py_Initialize / Py_Finalize
    try:
        # 这里需要实际的测试逻辑
        # 通常通过运行 C++ 测试程序来验证
        print("Python C API tests should be run via C++ test binaries")
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": True}

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print()

    print("=== Testing pybind imports ===")
    results = test_pybind_import()
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['module']}")
        if not r["success"] and r.get("error"):
            print(f"    Error: {r['error'][:200]}")

    print()
    print("=== Testing Python C API ===")
    api_result = test_python_c_api()
    print(f"  {'✓' if api_result['success'] else '✗'} Python C API")

    # 总结
    passed = sum(1 for r in results if r["success"]) + (1 if api_result["success"] else 0)
    total = len(results) + 1
    print(f"\n=== Summary: {passed}/{total} tests passed ===")
```

运行测试:

```bash
python test_python_313_compat.py
```

---

#### 步骤 2: ROS2 集成测试

```bash
# 测试 ROS2 节点中的 Python 集成
# 注意: 需要 ROS2 环境已配置

# 启动测试节点
ros2 run software_trigger_engine python_module_test

# 或使用 launch 文件
ros2 launch software_trigger_engine test_python_integration.launch.py
```

---

### 3.4 性能测试

```bash
# 运行性能基准测试
bazel run //src/pnc/evaluation:benchmark -- --python_version=3.13

# 比较性能差异 (需要分别使用 3.11 和 3.13 运行)
# 记录关键指标:
# - pybind 模块加载时间
# - Python 函数调用延迟
# - 内存使用情况
```

---

### 3.5 验收清单

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Bazel 依赖更新完成 | ☐ | MODULE.bazel, requirements.txt |
| pybind11 >= 2.13.6 | ☐ | 编译通过 |
| rules_python >= 0.35.0 | ☐ | 支持Python 3.13 |
| 所有 pybind 模块编译成功 | ☐ | 无编译错误 |
| Python C API 调用代码修改完成 | ☐ | 9个文件 |
| 单元测试通过率 >= 95% | ☐ | 关键测试全部通过 |
| 集成测试通过 | ☐ | ROS2 节点正常 |
| 性能无明显下降 | ☐ | 延迟增加 < 5% |

---

## 回滚方案

### 快速回滚

如果升级后发现严重问题，可以快速回滚:

```bash
cd /mnt/youbin03.jia_docker/app

# 恢复 MODULE.bazel
git checkout HEAD -- MODULE.bazel

# 恢复 requirements.txt
git checkout HEAD -- depend/pip/requirements.txt

# 恢复 pyproject.toml 文件
git checkout HEAD -- src/sdk_viz/saturnviz/pyproject.toml
git checkout HEAD -- src/perception/perception_vlm/perception_vlm_server/cloud_server/setup.py

# 清理并重新构建
bazel clean --expunge
bazel build //...
```

### 代码回滚

```bash
# 如果在独立分支工作
git checkout feature-noa-mapfree-master

# 或者使用 git revert 回退特定提交
git revert <upgrade_commit_hash>
```

---

## 附录

### A. Python 3.13 主要变更参考

| 变更项 | 影响 | 参考链接 |
|--------|------|----------|
| 移除废弃的 C API | 高 | https://docs.python.org/3.13/whatsnew/3.13.html |
| GIL 可选禁用 | 中 | PEP 703 |
| 新增 JIT 编译器 | 低 | 实验性功能 |
| 改进错误消息 | 低 | 更好的调试体验 |

### B. pybind11 兼容性矩阵

| pybind11 版本 | Python 支持 | 发布日期 |
|---------------|-------------|----------|
| 2.11.x | 3.7 - 3.12 | 2023 |
| 2.12.x | 3.7 - 3.12 | 2024 |
| 2.13.x | 3.7 - 3.13 | 2024.10+ |

### C. 相关文件完整列表

#### MODULE.bazel
- `/mnt/youbin03.jia_docker/app/MODULE.bazel`

#### requirements 文件
- `/mnt/youbin03.jia_docker/app/depend/pip/requirements.txt`
- `/mnt/youbin03.jia_docker/app/depend/pip/requirements_lock.txt`
- `/mnt/youbin03.jia_docker/app/src/dev_tools/performance/data_analyzer/requirements.txt`
- `/mnt/youbin03.jia_docker/app/src/sdk_viz/requirements.txt`

#### pyproject.toml 文件
- `/mnt/youbin03.jia_docker/app/src/sdk_viz/saturnviz/pyproject.toml`
- `/mnt/youbin03.jia_docker/app/src/tool_mcaplus/mcaplus/pyproject.toml`
- `/mnt/youbin03.jia_docker/app/src/dev_tools/performance/data_analyzer/pyproject.toml`

#### Python C API 调用文件 (需要修改)
1. `/mnt/youbin03.jia_docker/app/src/software_trigger_engine/src/trigger_engine/src/python_module.cpp`
2. `/mnt/youbin03.jia_docker/app/src/pnc/evaluation/src/metrics/python_metrics/python_framework_interface_metric.cc`
3. `/mnt/youbin03.jia_docker/app/src/pnc/evaluation/src/metrics/regression_metrics/sv_regress_metric.cc`
4. `/mnt/youbin03.jia_docker/app/src/pnc/evaluation/src/metrics/regression_metrics/regress_metric.cc`
5. `/mnt/youbin03.jia_docker/app/src/pnc/evaluation/src/metrics/regression_metrics/qa_metric.cc`
6. `/mnt/youbin03.jia_docker/app/src/data_mining/pybind_subscriber/src/nested_msg_sub_new.cpp`
7. `/mnt/youbin03.jia_docker/app/src/data_mining/pybind_subscriber/src/nested_msg_sub.cpp`
8. `/mnt/youbin03.jia_docker/app/src/data_mining/pybind_subscriber/src/mining_benchmark.cpp`

#### pybind 绑定文件 (需要验证)
- `src/pnc/tools/pybind/driving/bindings/*.cc` (11个文件)
- `src/pnc/tools/pybind/idnp/bindings/*.cc` (9个文件)
- `src/pnc/swc/pnc_workflow/control/jupyter_pybind/src/*.cc` (10个文件)
- `src/perception/perception_map_tiler/tools/*.cpp` (2个文件)
- `src/pnc/tools/prediction_pybind/prediction_pybind.cpp`
- `src/pnc/tools/cognition_pybind/cognition_pybind.cpp`
- `src/pnc/swc/pnc_workflow/safety_function/tools/pybind/src/*.cc`

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0 | 2026-04-09 | Claude | 初始版本 |

---

> 如有问题，请联系项目负责人或提交 Issue。


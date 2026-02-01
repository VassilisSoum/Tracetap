# Contract Verification Guide

See [Contract Testing in Features](../features/contract-testing.md) for comprehensive contract testing documentation.

This guide complements the features guide with practical verification workflows.

## Quick Start

### 1. Create Contract

```bash
python -c "
from src.tracetap.contract import ContractCreator
import json

with open('api.json') as f:
    captures = json.load(f)

creator = ContractCreator(provider='my-service', consumer='client')
contract = creator.create_from_captures(captures['requests'])

with open('contract.json', 'w') as f:
    json.dump(contract, f, indent=2)
"
```

### 2. Generate Verification Tests

```bash
python -c "
from src.tracetap.contract import ContractVerifier
import json

with open('contract.json') as f:
    contract = json.load(f)

verifier = ContractVerifier(contract)
tests = verifier.generate_tests(
    language='python',
    framework='pytest',
    base_url='http://localhost:3000'
)

with open('tests/test_contract.py', 'w') as f:
    f.write(tests)
"
```

### 3. Run Verification

```bash
pytest tests/test_contract.py -v
```

## Integration with CI/CD

See the [Contract Testing Feature Guide](../features/contract-testing.md#cicd-integration) for complete CI/CD examples.

## Troubleshooting

See the [Contract Testing Feature Guide](../features/contract-testing.md#troubleshooting) for common issues and solutions.

## Next Steps

- **[Full Contract Testing Guide](../features/contract-testing.md)** - Comprehensive documentation
- **[CI/CD Integration](ci-cd-integration.md)** - Automate contract verification

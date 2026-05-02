# Signal Count Gensyn Testnet Contracts

## Network

| Field | Value |
| --- | --- |
| Chain | Gensyn Testnet |
| Chain ID | `685685` |
| RPC used for deployment | `https://gensyn-testnet.g.alchemy.com/public` |
| Explorer base URL | `https://gensyn-testnet.explorer.alchemy.com` |

## Deployment Status

Status: deployed.

The deployment script is `contracts/script/DeployGensynTestnet.s.sol`. It
checks `block.chainid == 685685` before broadcasting.

## Contract Addresses

| Contract | Address | Deployment Transaction | Explorer |
| --- | --- | --- | --- |
| `SignalAgentRegistry` | `0x9Aa7E223B5bd2384cea38F0d2464Aa6cbB0146A9` | `0x14efd87d470b9720316350b24af1a3a2f84db503fa902ea1019db02809e1a510` | <https://gensyn-testnet.explorer.alchemy.com/tx/0x14efd87d470b9720316350b24af1a3a2f84db503fa902ea1019db02809e1a510> |
| `SignalTaskRegistry` | `0x7b0ED22C93eBdF6Be5c3f6D6fC8F7B51fdFBd861` | `0x93d2181c7206641a212aab7a62b56c0df6b0815bd0c63243a21652b35183a2eb` | <https://gensyn-testnet.explorer.alchemy.com/tx/0x93d2181c7206641a212aab7a62b56c0df6b0815bd0c63243a21652b35183a2eb> |
| `SignalReceiptRegistry` | `0xb67E197538F2cF9d398c28ec85d4f99fb2e668cf` | `0x3faa4376dc97f5e656a65f96d999e38e49f01ad85357b910dd3f4c3a5c78ca16` | <https://gensyn-testnet.explorer.alchemy.com/tx/0x3faa4376dc97f5e656a65f96d999e38e49f01ad85357b910dd3f4c3a5c78ca16> |

## Deployment Verification

| Contract | Block | Receipt Status | Gas Used | Bytecode Check |
| --- | ---: | --- | ---: | --- |
| `SignalAgentRegistry` | `17832314` | `1 (success)` | `428060` | non-empty bytecode |
| `SignalTaskRegistry` | `17832314` | `1 (success)` | `451393` | non-empty bytecode |
| `SignalReceiptRegistry` | `17832314` | `1 (success)` | `725993` | non-empty bytecode |

Deployer balance before deployment was `0.080000000000000000` test ETH.
Deployer balance after deployment was `0.079999972084305578` test ETH.

## Evidence Notes

- The transactions above are real Gensyn Testnet deployment transactions.
- No REE verification is claimed by these contracts.
- These contracts are the on-chain recording layer; backend chain integration is
  configured separately by the application runtime.

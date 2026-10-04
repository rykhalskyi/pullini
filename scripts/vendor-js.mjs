import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const rootDir = resolve(scriptDir, '..')

const bundles = [['mermaid/dist/mermaid.min.js', 'static/js/vendor/mermaid.min.js']]

for (const [from, to] of bundles) {
	const source = resolve(rootDir, 'node_modules', from)
	const target = resolve(rootDir, to)
	mkdirSync(dirname(target), { recursive: true })
	copyFileSync(source, target)
	console.log(`${to} updated`)
}

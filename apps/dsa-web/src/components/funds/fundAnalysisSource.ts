export function parseFundCodeInput(value: string): string[] {
  return value.trim().split(/[\s,，;；]+/).filter(Boolean);
}

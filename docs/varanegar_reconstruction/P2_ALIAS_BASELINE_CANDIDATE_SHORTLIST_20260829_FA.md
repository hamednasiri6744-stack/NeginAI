# Shortlist شواهد Baseline برای P2 ـ ۲۰۲۶-۰۸-۲۹

شش Packet/۴۲ Case اولویت P2 بررسی شد. پنج Packet دارای کاندید policy/lifecycle و `tour_payment.save_changes` دارای explicit-none است. هفت Action reference شامل ۸۷ Case پایه و ۳۸ kind-overlap ثبت شد.

برای pricing، `contextual_price.save`، `discount_rule.save` و `pricing.publish_linear_discount_version` کاندیدهای family هستند. برای `received_cheque.edit` سه کاندید change-status، undo و validate-transition ثبت شد. categoryهای baseline با نگاشت محدود `happy_path→success`، `invariant→validation` و `fault_injection→failure_injection` نرمال شدند؛ این فقط ابزار مقایسه است.

هیچ Action string دقیق، Candidate پذیرفته، Case اجراشده یا readiness وجود ندارد. lower bound طراحی ۱۴۰۴ و پایهٔ Risk/Trace برابر ۸۴/۳۴۳ ثابت است.

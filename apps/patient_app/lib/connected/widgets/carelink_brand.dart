import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class CareLinkBrand extends StatelessWidget {
  const CareLinkBrand({super.key, this.compact = false});
  final bool compact;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        padding: EdgeInsets.all(compact ? 9 : 12),
        decoration: BoxDecoration(
          color: AppTheme.teal,
          borderRadius: BorderRadius.circular(compact ? 14 : 18),
        ),
        child: Icon(
          Icons.favorite_border_rounded,
          size: compact ? 24 : 30,
          color: Colors.white,
        ),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            'CareLink',
            style: TextStyle(
              color: const Color(0xFF0F172A),
              fontSize: compact ? 23 : 30,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.6,
            ),
          ),
        ),
      ),
    ],
  );
}
